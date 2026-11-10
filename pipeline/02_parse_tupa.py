"""Convierte el OCR del TUPA (un .txt por página) en data/tupa_huayucachi.json.

Uso:  python pipeline/02_parse_tupa.py <carpeta_txt> [ultima_pagina_fichas]

El TUPA 2023 de Huayucachi (Ordenanza N° 005-2022-CM/MDCHI) tiene:
  - págs. 1–8: ordenanza
  - págs. 9–104: fichas SUT de cada procedimiento (lo que le sirve al vecino)
  - págs. 105–404: sustento de costos (no se indexa)
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "ocr/txt")
ULTIMA = int(sys.argv[2]) if len(sys.argv) > 2 else 104
OUT = Path(__file__).resolve().parent.parent / "data" / "tupa_huayucachi.json"

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
        if 9 <= n <= ULTIMA:
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
    tras = t[t.find("Plazo de atenci"):] if "Plazo de atenci" in t else ""
    plazo = re.search(r"(\d{1,3})\s*d[ií]as?\s*n?h[aá]biles", tras[:600], re.I)
    calif = re.search(r"(Aprobaci[oó]n autom[aá]tica|Evaluaci[oó]n previa\s*[-—–]\s*Silencio Administrativo (?:Positivo|Negativo))", t, re.I)
    unidad = entre(t, r"Unidad de organizaci[oó]n donde se presenta la documentaci[oó]n", r"\n\|?\s*Unidad de organizaci[oó]n responsable")
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


# Correcciones verificadas a mano contra la imagen del PDF (el OCR leyó mal estos campos)
CORRECCIONES = {
    "38–41": {"plazo": "7 días hábiles", "costo": "S/ 971.10"},
}


def main():
    procs = [parse(b) for b in bloques()]
    for p in procs:
        p.update(CORRECCIONES.get(p["paginas"], {}))
    data = {
        "meta": {
            "fuente": "TUPA de la Municipalidad Distrital de Huayucachi (PDF escaneado, 404 págs.)",
            "norma": "Ordenanza Municipal N° 005-2022-CM/MDCHI (13/12/2022)",
            "url": "https://drive.google.com/file/d/1oYUDl-Vtx1KLbppotWYfYg5IYguCytQE/view",
            "portal": "https://www.transparencia.gob.pe/enlaces/pte_transparencia_enlaces.aspx?id_entidad=11095&id_tema=5",
            "ocr": "Tesseract 5 (spa), 200 dpi – ver pipeline/01_ocr.sh",
        },
        "procedimientos": procs,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(procs)} procedimientos -> {OUT}")
    for p in procs:
        print(f"[{p['paginas']:>7}] {p['codigo']:<12} {p['costo']:<10} {p['plazo']:<16} {p['nombre'][:70]}")


if __name__ == "__main__":
    main()
