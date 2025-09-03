import re
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def clean_space(s: str) -> str:
    if not s:
        return ""
    # normaliza espaços e quebras de linha
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def normalize_href(href: str) -> str:
    """Remove quebras de linha e espaços 'soltos' do meio do href."""
    if not href:
        return href
    href = href.replace("\r", "").replace("\n", "")
    href = re.sub(r"\s+", "", href)
    return href

def ensure_excel_path(path: Path) -> Path:
    """Se o arquivo estiver aberto, cria um nome alternativo com sufixo."""
    try:
        if path.exists():
            # teste de escrita
            with open(path, "ab"):
                pass
        return path
    except PermissionError:
        alt = path.with_name(f"{path.stem} (novo).xlsx")
        log.warning("Arquivo Excel em uso. Salvando como: %s", alt)
        return alt

def is_probably_pdf_bytes(b: bytes) -> bool:
    # PDF geralmente começa com %PDF e contém '%%EOF' ao final
    return b.startswith(b"%PDF") and (b.rfind(b"%%EOF") != -1)
