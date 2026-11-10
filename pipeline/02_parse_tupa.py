"""Convierte el texto de un TUPA (un .txt por página) en data/municipios/<slug>.json.

Uso:  python pipeline/02_parse_tupa.py <slug>
      (la configuración de cada municipalidad está en data/municipios.json)

Funciona con cualquier TUPA en formato SUT (fichas "Denominación del Procedimiento…"),
venga de OCR (PDF escaneado) o de pdftotext (PDF digital). Agregar una municipalidad:
  1. bash pipeline/01_ocr.sh tupa.pdf data/<slug>_paginas      (o pdftotext si es digital)
  2. añadir su entrada en data/municipios.json
  3. python pipeline/02_parse_tupa.py <slug>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = sys.argv[1] if len(sys.argv) > 1 else "huayucachi"
CFG = json.loads((ROOT / "data" / "municipios.json").read_text(encoding="utf-8"))[SLUG]
SRC = ROOT / CFG["paginas_txt"]
OUT = ROOT / "data" / "municipios" / f"{SLUG}.json"

INICIO = re.compile(r"Denominaci[oó]n del (Procedimiento|Servicio)", re.I)
# basura típica del OCR en los márgenes (sellos, numeración de folios)
RUIDO = re.compile(r"^[\W\d_]{0,6}(?=\S)")


def limpiar_linea(l: str) -> str:
    l = l.strip()
    l = re.sub(r"^[^A-Za-zÁÉÍÓÚÑáéíóúñ0-9\"“(]{1,4}\s+", "", l)  # basura al inicio
    l = re.sub(r"^(?:[A-Za-zÁÉÍÓÚÑáéíóú¡¿]{1,2}\s+){1,2}(?=[A-ZÁÉÍÓÚ\"“0-9])", "", l)  # 'E ', 'í ', 'Doa '
    return l.strip()


def paginas():
    for f in sorted(SRC.glob("*.txt")):
        n = int(f.stem[:3])
        if CFG["pag_ini"] <= n <= CFG["pag_fin"]:
            yield n, f.read_text(encoding="utf-8", errors="ignore")


def bloques():
    actual = None
    for n, t in paginas():
        if INICIO.search(t):
            if actual:
                yield actual
            actual = {"pags": [n], "texto": t}
        elif actual:
            actual["pags"].append(n)
            actual["texto"] += "\n" + t
    if actual:
        yield actual


def entre(texto, a, b):
    m = re.search(a + r"(.*?)" + b, texto, re.S | re.I)
    return m.group(1).strip() if m else ""


def parse(b):
    lineas = [limpiar_linea(l) for l in b["texto"].splitlines()]
    lineas = [l for l in lineas if len(l) > 2 and not l.startswith("Texto Único de Procedimientos")]
    t = "\n".join(lineas)

    nombre = entre(t, r"Denominaci[oó]n del (?:Procedimiento|Servicio)[^\n]*\n", r"\n[^\n]{0,6}(?:C[oóa]digo|\|?\s*Descripci)")
    q = re.search(r"[\"“”]", nombre)  # el nombre va entre comillas: corta la basura previa
    if q:
        nombre = nombre[q.start():]
    nombre = re.sub(r"\n[^A-Za-zÁÉÍÓÚÑ(]{0,6}", " ", nombre)
    nombre = re.sub(r"\s+", " ", nombre).strip(" \"“”'|")
    nombre = re.sub(r"\s+[\"”(]?\s*\(?v\]?$", "", nombre).replace("[TSE", "ITSE").replace("(Con TSE", "(Con ITSE")
    nombre = re.sub(r"^insp\w+ci[oó]n", "Inspección", nombre).replace("objeto de is OPE con", "objeto de inspección clasificados con")
    codigo = re.search(r"C[oóa]digo:?\s*([A-Z]{2}[0-9A-Z]{8,10})", t)
    desc = entre(t, r"Descripci[oó]n del (?:procedimiento|servicio)", r"\n[^\n]{0,8}Requisitos\b")
    req_txt = entre(t, r"\n[^\n]{0,8}Requisitos\b", r"\n[^\n]{0,8}(?:Notas:|Formularios|Canales de atenci)")
    requisitos = [re.sub(r"\s+", " ", r).strip() for r in re.split(r"\n?\s*\d{1,2}\s?[\.\-]{1,2}\s?-?\s*", req_txt) if len(r.strip()) > 8]
    monto = re.search(r"M[oa][nm]?a?to\s*-?\s*[S5]{1,2}/\s*\.?\s*([\d]+[.,]\d{2})", t)
    gratuito = re.search(r"Gratuito", t, re.I)
    mp = re.search(r"^[^\n]{0,8}Plazo(?: de atenci[oó]n)?\b(?! m[aá]ximo)", t, re.M)
    tras = t[mp.start():] if mp else ""
    plazo = re.search(r"(\d{1,3})\s*d[ií]as?\s*n?h[aá]bil(?:es)?", tras[:600], re.I)
    calif = re.search(r"(Aprobaci[oó]n autom[aá]tica|Evaluaci[oó]n previa\s*[-—–]\s*Silencio Administrativo (?:Positivo|Negativo))", t, re.I)
    unidad = entre(t, r"Unidad de organizaci[oó]n donde se presenta la documentaci[oó]n", r"\n[^\n]{0,8}Unidad de organizaci[oó]n responsable")
    responsable = entre(t, r"responsable de aprobar la solicitud[^\n]*\n", r"\n")
    horario = re.search(r"(Lunes a Viernes[^\n]+)", t)

    costo = f"S/ {monto.group(1).replace(',', '.')}" if monto else ("Gratuito" if gratuito else "")
    donde = re.sub(r"\s+", " ", unidad.replace("|", " ")).strip(" :")
    if horario:
        donde = f"{donde}. {horario.group(1).strip()}" if donde else horario.group(1).strip()
    return {
        "nombre": nombre or "Procedimiento sin nombre legible",
        "codigo": codigo.group(1) if codigo else "",
        "tipo": "Servicio" if "Denominación del Servicio" in t else "Procedimiento",
        "descripcion": re.sub(r"\s+", " ", desc),
        "requisitos": requisitos[:12],
        "costo": costo,
        "plazo": f"{plazo.group(1)} días hábiles" if plazo else ("Inmediato (aprobación automática)" if calif and "autom" in calif.group(1).lower() else ""),
        "calificacion": calif.group(1) if calif else "",
        "donde": donde,
        "responsable": re.sub(r"\s+", " ", responsable.replace("|", " ")).strip(),
        "paginas": f"{b['pags'][0]}–{b['pags'][-1]}" if len(b["pags"]) > 1 else str(b["pags"][0]),
        "texto": t,
    }


def main():
    procs = [parse(b) for b in bloques()]
    for p in procs:
        # correcciones verificadas a mano contra la imagen del PDF (el OCR leyó mal esos campos)
        p.update(CFG.get("correcciones", {}).get(p["paginas"], {}))
    meta = {k: v for k, v in CFG.items() if k not in ("correcciones", "paginas_txt", "pag_ini", "pag_fin")}
    data = {"meta": {"slug": SLUG, **meta}, "procedimientos": procs}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(procs)} procedimientos -> {OUT}")
    for p in procs:
        print(f"[{p['paginas']:>7}] {p['codigo']:<12} {p['costo']:<10} {p['plazo']:<16} {p['nombre'][:70]}")


if __name__ == "__main__":
    main()
