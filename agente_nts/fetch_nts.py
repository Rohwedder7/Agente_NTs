from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Iterable, List, Optional
import requests
from bs4 import BeautifulSoup

from .settings import (
    PORTAL_LIST_URL, USER_AGENT, REQUEST_TIMEOUT, PDF_DIR, MIN_DATE
)
from .utils import normalize_href, is_probably_pdf_bytes

log = logging.getLogger(__name__)

@dataclass
class NTLink:
    titulo: str                # Ex.: "Nota Técnica 2025.002-RTC - Versão 1.20"
    publicada_em: Optional[date]
    href_pdf: str              # link do PDF (exibirArquivo.aspx?conteudo=...)
    slug: str                  # hash ou codificação do href p/ nomear arquivo

LIST_ROW_RE = re.compile(r"Nota\s+Técnica\s+(\d{4}\.\d{3}.*)", re.I)
PUBLI_RE = re.compile(r"Publicada\s+em\s+(\d{2}/\d{2}/\d{4})", re.I)

def _parse_publish_date(txt: str) -> Optional[date]:
    m = PUBLI_RE.search(txt)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d/%m/%Y").date()
    except Exception:
        return None

def discover_nts_by_publish_date(min_date: date = MIN_DATE) -> List[NTLink]:
    """
    Varre a página de lista de NTs do Portal e captura:
      - título
      - data de publicação
      - link do PDF
    Filtra por data >= min_date.
    """
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(PORTAL_LIST_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    nts: List[NTLink] = []
    for a in soup.select("a[href*='exibirArquivo.aspx']"):
        raw_href = a.get("href")
        href = normalize_href(raw_href)
        if not href:
            continue

        # tenta localizar bloco de texto que contenha "Publicada em"
        parent_text = " ".join(a.find_parent().get_text(" ", strip=True).split()) if a.find_parent() else ""
        titulo = a.get_text(" ", strip=True)
        publicada = _parse_publish_date(parent_text) or _parse_publish_date(titulo)

        # monta URL absoluta se vier relativa
        if href.startswith("/"):
            href_pdf = f"https://www.nfe.fazenda.gov.br{href}"
        elif href.lower().startswith("http"):
            href_pdf = href
        else:
            href_pdf = f"https://www.nfe.fazenda.gov.br/portal/{href}"

        # slug simples para nomear o arquivo
        slug = re.sub(r"[^a-zA-Z0-9]+", "", href_pdf.split("conteudo=")[-1])[:32]
        if not slug:
            slug = re.sub(r"[^a-zA-Z0-9]+", "", titulo)[:32] or "nt"

        if publicada and publicada >= min_date:
            nts.append(NTLink(titulo=titulo, publicada_em=publicada, href_pdf=href_pdf, slug=slug))

    # remove duplicados por href
    seen = set()
    unique = []
    for nt in nts:
        if nt.href_pdf in seen:
            continue
        seen.add(nt.href_pdf)
        unique.append(nt)

    log.info("Encontradas %d NTs com ano >= %s", len(unique), min_date.year)
    return unique

def ensure_pdf_downloaded(nt: NTLink) -> Optional[Path]:
    """
    Baixa o PDF. Se vier HTML, salva como .html e retorna None.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.nfe.fazenda.gov.br/portal/",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(nt.href_pdf, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        log.error("Falha no download %s: %s", nt.href_pdf, e)
        return None

    content_type = resp.headers.get("Content-Type", "")
    content = resp.content or b""

    if "pdf" in content_type.lower() or is_probably_pdf_bytes(content):
        out = PDF_DIR / f"{nt.slug}.pdf"
        out.write_bytes(content)
        return out
    else:
        # salva HTML para análise posterior
        out = PDF_DIR / f"{nt.slug}.html"
        out.write_text(resp.text, encoding=resp.encoding or "utf-8", errors="ignore")
        log.warning("Conteúdo não-PDF para %s (salvo como HTML).", nt.titulo)
        return None
