# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import date

# Página oficial "Notas Técnicas"
PORTAL_LIST_URL = "https://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=04BIflQt1aY="

# Filtro pela DATA DE PUBLICAÇÃO exibida no site ("Publicada em dd/mm/aaaa")
START_PUBLISH_DATE = date(2025, 1, 1)

# Diretórios
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_XLSX = OUTPUT_DIR / "resultado_nts.xlsx"

# HTTP
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Extração de tabela (pdfplumber) – pode ajustar se precisar ser mais ou menos sensível
TABLE_SETTINGS_PRIMARY = {
    "vertical_strategy": "lines",
    "horizontal_strategy": "lines",
    "snap_tolerance": 3,
    "intersection_tolerance": 5,
    "min_words_vertical": 2,
    "min_words_horizontal": 2,
    "keep_blank_chars": False,
}
TABLE_SETTINGS_FALLBACK = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
    "explicit_vertical_lines": [],
    "explicit_horizontal_lines": [],
    "keep_blank_chars": False,
}
