"""Wayki: núcleo del asistente de trámites municipales.

- Recuperación (la "R" de RAG): TF-IDF sobre los procedimientos del TUPA de cada
  municipalidad (data/municipios/<slug>.json), extraídos del PDF oficial (ver pipeline/).
  Piloto: Huayucachi (PDF escaneado, OCR). Segunda: El Tambo (PDF digital).
- Generación: un LLM (Llama 3.3 70B vía Groq) responde SOLO con el contexto recuperado
  y devuelve JSON estructurado (requisitos, costo, plazo, dónde ir, página del TUPA).
- Voz: Whisper (whisper-large-v3-turbo vía Groq) convierte el audio del vecino en texto.

Sin API key la app sigue funcionando en "modo sin IA": muestra la ficha del
procedimiento más parecido, extraída directamente del TUPA.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "municipios"


def listar_municipios() -> dict[str, str]:
    """slug -> nombre corto, de las municipalidades con TUPA procesado."""
    out = {}
    for f in sorted(DATA_DIR.glob("*.json")):
        meta = json.loads(f.read_text(encoding="utf-8"))["meta"]
        out[f.stem] = meta.get("corto", f.stem)
    # el piloto primero
    return dict(sorted(out.items(), key=lambda kv: kv[0] != "huayucachi"))
GROQ_URL = "https://api.groq.com/openai/v1"
# Si Groq retira un modelo, se prueba el siguiente (ver console.groq.com/docs/models)
LLM_MODELS = [m for m in [os.getenv("WAYKI_LLM_MODEL"), "llama-3.3-70b-versatile",
                          "openai/gpt-oss-120b", "llama-3.1-8b-instant"] if m]
STT_MODEL = os.getenv("WAYKI_STT_MODEL", "whisper-large-v3-turbo")

# Palabras de vecinos -> palabras del TUPA (el TUPA habla "en jurídico").
SINONIMOS = {
    "bodega": "bodega licencia funcionamiento",
    "tienda": "licencia funcionamiento establecimiento",
    "negocio": "licencia funcionamiento establecimiento",
    "restaurante": "licencia funcionamiento establecimiento riesgo",
    "local": "establecimiento",
    "abrir": "licencia funcionamiento",
    "defensa civil": "inspeccion tecnica seguridad edificaciones itse",
    "casarme": "matrimonio celebracion pliego matrimonial",
    "casar": "matrimonio celebracion pliego matrimonial",
    "boda": "matrimonio celebracion",
    "construir": "licencia edificacion modalidad",
    "casa": "edificacion vivienda",
    "terreno": "predio posesion",
    "lote": "predio subdivision",
    "partida": "expedicion partidas actas copia certificada",
    "nacimiento": "acta nacimiento registro civil",
    "informacion": "acceso informacion publica",
    "fiesta": "espectaculos publicos",
    "concierto": "espectaculos publicos",
    "cartel": "anuncio publicitario",
    "letrero": "anuncio publicitario",
    "mototaxi": "vehiculos menores transporte",
    "cerrar": "cese actividades cese actividades",
    "cierro": "cese actividades",
    "dar de baja": "cese actividades",
    "traspasar": "transferencia licencia funcionamiento",
    "traspaso": "transferencia licencia funcionamiento",
    "vender mi negocio": "transferencia licencia funcionamiento",
    "cambiar de rubro": "cambio giro",
    "cambiar de giro": "cambio giro",
    "perdi": "duplicado certificado",
    "duplicado": "duplicado certificado",
    "vencio": "renovacion certificado",
    "renovar": "renovacion certificado",
    "mercado": "mercados abastos galerias",
    "galeria": "mercados abastos galerias",
    "puesto": "cesionarios mercados",
    "alquilo un espacio": "cesionarios",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def expandir(pregunta: str) -> str:
    q = normalizar(pregunta)
    extra = [v for k, v in SINONIMOS.items() if re.search(rf"\b{k}\b", q)]
    return q + " " + " ".join(extra)


@dataclass
class Resultado:
    proc: dict
    score: float


class BuscadorTUPA:
    def __init__(self, slug: str = "huayucachi"):
        data = json.loads((DATA_DIR / f"{slug}.json").read_text(encoding="utf-8"))
        self.meta = data["meta"]
        self.procs = data["procedimientos"]
        # el nombre pesa más que el resto del texto
        docs = [normalizar((p["nombre"] + " ") * 3 + p["texto"]) for p in self.procs]
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
        self.M = self.vec.fit_transform(docs)

    def buscar(self, pregunta: str, k: int = 4, umbral: float = 0.055) -> list[Resultado]:
        """Top-k procedimientos. Si el mejor no supera el umbral, la pregunta está fuera del TUPA indexado."""
        sims = cosine_similarity(self.vec.transform([expandir(pregunta)]), self.M)[0]
        idx = sims.argsort()[::-1][:k]
        if sims[idx[0]] < umbral:
            return []
        return [Resultado(self.procs[i], float(sims[i])) for i in idx if sims[i] > 0]


SYSTEM = """Eres Wayki, asistente de trámites de la {municipio} (Perú).
Respondes a vecinos en español sencillo, cálido y breve (nada de jerga legal).
REGLAS:
- Usa SOLO la información de los fragmentos del TUPA que te doy. No inventes requisitos, montos ni plazos.
- Si el texto OCR está dañado o falta un dato, dilo ("no se lee en el TUPA, confirma en mesa de partes").
- Si ningún fragmento responde la pregunta, pon encontrado=false y sugiere llamar o ir a la municipalidad.
Devuelve SOLO un JSON con esta forma:
{"encontrado": bool,
 "procedimiento": str,
 "codigo": str,
 "resumen": str,            // 1-2 frases: qué es y si aplica a su caso
 "requisitos": [str],       // lista corta, en palabras simples
 "costo": str,              // ej. "S/ 91.10" o "Gratuito" o "No se indica"
 "plazo": str,              // ej. "9 días hábiles"
 "donde": str,              // oficina y horario
 "consejo": str,            // 1 consejo práctico para no regresar dos veces
 "pagina_tupa": str}        // páginas del PDF de donde sale
"""


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def responder(pregunta: str, resultados: list[Resultado], api_key: str,
              municipio: str = "Municipalidad Distrital de Huayucachi") -> dict:
    contexto = "\n\n".join(
        f"### Fragmento {i+1} (páginas {r.proc['paginas']}, código {r.proc.get('codigo') or 's/c'})\n"
        f"{r.proc['nombre']}\n{r.proc['texto'][:2500]}"
        for i, r in enumerate(resultados[:5])
    )
    body = {
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM.replace("{municipio}", municipio)},
            {"role": "user", "content": f"Pregunta del vecino: {pregunta}\n\nFragmentos del TUPA:\n{contexto}"},
        ],
    }
    for model in LLM_MODELS:
        r = requests.post(f"{GROQ_URL}/chat/completions", json={**body, "model": model},
                          headers=_headers(api_key), timeout=60)
        if r.status_code in (400, 404) and "model" in r.text.lower():
            continue  # modelo retirado o no disponible: probar el siguiente
        r.raise_for_status()
        break
    r.raise_for_status()
    out = r.json()
    ans = json.loads(out["choices"][0]["message"]["content"])
    ans["_tokens"] = {**out.get("usage", {}), "model": out.get("model")}
    return ans


def transcribir(audio_bytes: bytes, api_key: str, filename: str = "audio.wav") -> str:
    r = requests.post(
        f"{GROQ_URL}/audio/transcriptions",
        headers=_headers(api_key),
        files={"file": (filename, audio_bytes)},
        data={"model": STT_MODEL, "language": "es", "response_format": "json",
              "prompt": "Trámites municipales en Huancayo: licencia, TUPA, ITSE, matrimonio, partida."},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["text"].strip()


def ficha_sin_ia(res: Resultado, municipio: str = "la municipalidad") -> dict:
    """Respuesta sin LLM: los campos que el parser sacó del TUPA."""
    p = res.proc
    return {
        "encontrado": True,
        "procedimiento": p["nombre"],
        "codigo": p.get("codigo") or "",
        "resumen": (p.get("descripcion") or "")[:400],
        "requisitos": p.get("requisitos") or [],
        "costo": p.get("costo") or "Ver TUPA",
        "plazo": p.get("plazo") or "Ver TUPA",
        "donde": p.get("donde") or f"Mesa de partes – {municipio}",
        "consejo": "Lleva copia de tu DNI y pregunta en mesa de partes si hay formulario.",
        "pagina_tupa": p["paginas"],
    }
