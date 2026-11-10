#!/bin/bash
# OCR del TUPA escaneado de Huayucachi (404 págs.) -> un .txt por página.
# Requisitos: poppler-utils (pdftoppm) y tesseract-ocr con idioma 'spa'.
# Uso: bash pipeline/01_ocr.sh "TUPA 2023.pdf" data/ocr_paginas [primera] [ultima]
set -e
PDF=${1:-"TUPA 2023.pdf"}; OUT=${2:-data/ocr_paginas}; INI=${3:-1}; FIN=${4:-104}
mkdir -p "$OUT" /tmp/wayki_img
ocr_page(){ p=$1; f=$(printf "%03d" $p); [ -s "$OUT/$f.txt" ] && return
  pdftoppm -r 200 -gray -f $p -l $p -png "$PDF" /tmp/wayki_img/$f >/dev/null 2>&1
  im=$(ls /tmp/wayki_img/$f*.png | head -1)
  tesseract "$im" "$OUT/$f" -l spa --psm 6 >/dev/null 2>&1; rm -f "$im"; }
export -f ocr_page; export PDF OUT
seq $INI $FIN | xargs -P 2 -I{} bash -c 'ocr_page {}'
echo "OCR listo en $OUT"
