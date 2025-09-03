from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pdfplumber
from pypdf import PdfReader

from .utils import clean_space

log = logging.getLogger(__name__)

@dataclass
class NTRow:
    nt_titulo: str
    nt_versao: Optional[str]
    publicada_em: Optional[str]
    implantacao_homolog: Optional[str]
    implantacao_producao: Optional[str]
    grupo: Optional[str]
    campo: Optional[str]
    regra: Optional[str]
    aplic: Optional[str]
    msg: Optional[str]
    descricao: Optional[str]

# -----------------------
# Helpers de parsing
# -----------------------

CONTROL_VER_RE = re.compile(r"Controle\s+de\s+Vers(ões|oes)", re.I)
HIST_CRONO_RE = re.compile(r"Hist(ó|o)rico\s+de\s+Altera(ç|c)(ões|oes)\s*/\s*Cronograma", re.I)
VERSAO_LINHA_RE = re.compile(r"^\s*(\d+\.\d+)\s+(\d{2}/\d{4}|[A-Za-z]+/\d{4}|Março/\d{4}|Junho/\d{4}|Julho/\d{4})\s+.*", re.I)

# capta RV cabeçalho e colunas
RV_SECTION_RE = re.compile(r"^\s*7\.\s*Regras\s+de\s+Valida(ç|c)(ão|ao)\s*", re.I)
COL_HINTS = ("Aplic.", "Msg", "Descrição", "Regra", "Campo")

DATE_DDMMYYYY = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")

def _pdf_text(path: Path) -> str:
    """Lê texto do PDF com pypdf como fallback do pdfplumber."""
    try:
        reader = PdfReader(str(path))
        parts = []
        for p in reader.pages:
            txt = p.extract_text() or ""
            parts.append(txt)
        return "\n".join(parts)
    except Exception as e:
        log.warning("Falha text pypdf em %s: %s", path.name, e)
        return ""

def _iter_tables(pl_page) -> List[List[List[str]]]:
    """
    Extrai múltiplos conjuntos de tabelas da página com estratégias diferentes.
    Sem 'keep_blank_chars' (compatível com pdfplumber atuais).
    """
    tables: List[List[List[str]]] = []

    common = dict(
        vertical_strategy="lines",
        horizontal_strategy="lines",
        snap_tolerance=3,
        join_tolerance=3,
        intersection_tolerance=3,
        edge_min_length=3,
        min_words_vertical=3,
        min_words_horizontal=1,
        text_tolerance=2,
    )

    for ts in (
        common,
        {**common, "vertical_strategy": "text", "horizontal_strategy": "text"},
        {**common, "vertical_strategy": "lines_strict", "horizontal_strategy": "lines_strict"},
    ):
        try:
            t = pl_page.extract_tables(table_settings=ts) or []
            if t:
                tables.extend(t)
        except Exception as e:
            log.debug("extract_tables falhou: %s", e)

    return tables

def _guess_has_rv_header(row: List[str]) -> bool:
    head = " | ".join((c or "").lower() for c in row)
    return ("aplic" in head and "msg" in head) or ("descri" in head and "regra" in head)

def _parse_rv_tables(path: Path) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            tables = _iter_tables(page)
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                # identifica cabeçalho
                header = None
                for r in tbl[:3]:
                    if _guess_has_rv_header([cell or "" for cell in r]):
                        header = [clean_space(cell or "") for cell in r]
                        break
                if not header:
                    continue

                # normaliza índices de colunas
                def find_idx(names: Iterable[str]) -> Optional[int]:
                    names = [n.lower() for n in names]
                    for i, h in enumerate(header):
                        h2 = h.lower()
                        if any(n in h2 for n in names):
                            return i
                    return None

                idx_regra = find_idx(("regra", "rv", "id"))
                idx_campo = find_idx(("campo", "id"))
                idx_aplic = find_idx(("aplic",))
                idx_msg = find_idx(("msg", "cstat"))
                idx_desc = find_idx(("descr", "descrição", "descricao", "observ"))

                for r in tbl[1:]:
                    cells = [clean_space(c or "") for c in r] + [""] * 6
                    row = dict(
                        campo=cells[idx_campo] if idx_campo is not None else "",
                        regra=cells[idx_regra] if idx_regra is not None else "",
                        aplic=cells[idx_aplic] if idx_aplic is not None else "",
                        msg=cells[idx_msg] if idx_msg is not None else "",
                        descricao=cells[idx_desc] if idx_desc is not None else "",
                    )
                    # precisa ter pelo menos descrição
                    if any(row.values()) and len(clean_space(row["descricao"])) >= 3:
                        out.append(row)
    return out

def _parse_rv_text(text: str) -> List[Dict[str, str]]:
    """
    Fallback textual: procura bloco 'Regras de Validação' e tenta quebrar em linhas com colunas.
    """
    out: List[Dict[str, str]] = []
    if not text:
        return out

    # encontra início da seção
    sec = RV_SECTION_RE.split(text, maxsplit=1)
    if len(sec) < 2:
        return out
    body = sec[1]

    # heurística: linhas com "Obrig."/"Facult." + "Rejeição:" etc
    for para in re.split(r"\n{2,}", body):
        p = clean_space(para)
        if not p:
            continue
        # tenta capturar padrões comuns
        aplic = None
        if re.search(r"\bObrig\.\b", p, re.I):
            aplic = "Obrig."
        elif re.search(r"\bFacult\.\b", p, re.I):
            aplic = "Facult."

        mmsg = re.search(r"\b(\d{3,4})\b", p)  # códigos 3-4 dígitos
        msg = mmsg.group(1) if mmsg else ""

        # “Regra de Validação” às vezes vem como “B09-20”, “E16a-30” etc
        mrv = re.search(r"\b([A-Z]{1,3}\d{1,3}[A-Za-z\-]*\d*)\b", p)
        regra = mrv.group(1) if mrv else ""

        # campo: tenta antes da RV, ex.: "B09-20" => Campo "B09"
        mcampo = re.match(r"^([A-Z]{1,3}\d{1,3})", regra) if regra else None
        campo = mcampo.group(1) if mcampo else ""

        # descrição: após "Rejeição:" ou após o código
        desc = p
        rej = re.search(r"Rejei(ç|c)ão:\s*(.*)$", p, re.I)
        if rej:
            desc = rej.group(2)
        else:
            # fallback: remove prefixos
            desc = re.sub(r"^(Obrig\.|Facult\.)\s*", "", desc, flags=re.I)

        if desc and (aplic or msg or regra):
            out.append(dict(campo=campo, regra=regra, aplic=aplic or "", msg=msg, descricao=desc))

    return out

def _extract_versions_block(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Retorna (versao_atual, dt_homolog, dt_producao) a partir do texto.
    Estratégia:
      - Acha 'Controle de Versões' e captura a última versão (ex.: 1.20)
      - Acha 'Histórico de Alterações / Cronograma' e pega a linha correspondente à versão (se possível)
      - Se houver múltiplas linhas, pega a última ocorrência visual no bloco.
    """
    versao = None
    dt_hml = None
    dt_prd = None

    # 1) versão
    mcv = CONTROL_VER_RE.search(text)
    if mcv:
        tail = text[mcv.end():]
        candidatas = []
        for ln in tail.splitlines()[:120]:
            ln = ln.strip()
            m = VERSAO_LINHA_RE.match(ln)
            if m:
                candidatas.append(m.group(1))  # versão X.YY
        if candidatas:
            versao = candidatas[-1]  # última listada (geralmente mais recente)

    # 2) cronograma
    mh = HIST_CRONO_RE.search(text)
    if mh:
        tail = text[mh.end():]
        # pega um pedaço limitado
        trecho = "\n".join(tail.splitlines()[:250])
        # captura todas as datas dd/mm/aaaa
        datas = DATE_DDMMYYYY.findall(trecho)
        # heurística: as duas últimas datas do bloco são Homolog e Produção
        if len(datas) >= 2:
            dt_hml = datas[-2]
            dt_prd = datas[-1]

    return versao, dt_hml, dt_prd

def extract_rules_from_pdf(
    pdf_path: Path,
    nt_titulo: str,
    publicada_em: Optional[str],
) -> List[NTRow]:
    """
    Extrai RVs e cronograma de uma NT em PDF.
    Retorna lista de NTRow.
    """
    rows: List[NTRow] = []
    text = _pdf_text(pdf_path)

    versao, dt_hml, dt_prd = _extract_versions_block(text)

    # 1º tenta tabelas
    table_rvs: List[Dict[str, str]] = []
    try:
        table_rvs = _parse_rv_tables(pdf_path)
    except Exception as e:
        log.debug("Falha tabelas em %s: %s", pdf_path.name, e)

    # fallback textual
    if not table_rvs:
        text_rvs = _parse_rv_text(text)
    else:
        text_rvs = []

    rvs = table_rvs or text_rvs

    if not rvs:
        # ainda retorna uma linha de metadados para que Homolog/Prod entrem na planilha
        rows.append(NTRow(
            nt_titulo=nt_titulo,
            nt_versao=versao,
            publicada_em=publicada_em,
            implantacao_homolog=dt_hml,
            implantacao_producao=dt_prd,
            grupo=None, campo=None, regra=None, aplic=None, msg=None, descricao=None
        ))
        return rows

    # tenta descobrir 'Grupo' por heurística textual anterior (opcional)
    grupo_atual = None
    for rv in rvs:
        rows.append(NTRow(
            nt_titulo=nt_titulo,
            nt_versao=versao,
            publicada_em=publicada_em,
            implantacao_homolog=dt_hml,
            implantacao_producao=dt_prd,
            grupo=grupo_atual,
            campo=clean_space(rv.get("campo", "")),
            regra=clean_space(rv.get("regra", "")),
            aplic=clean_space(rv.get("aplic", "")),
            msg=clean_space(rv.get("msg", "")),
            descricao=clean_space(rv.get("descricao", "")),
        ))

    return rows
