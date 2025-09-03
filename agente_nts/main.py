from __future__ import annotations
import logging
from dataclasses import asdict
from pathlib import Path
from typing import List

from .settings import OUTPUT_DIR
from .fetch_nts import discover_nts_by_publish_date, ensure_pdf_downloaded
from .parse_pdf import extract_rules_from_pdf, NTRow
from .excel import write_rules_to_xlsx

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
log = logging.getLogger(__name__)

OUTPUT_XLSX = OUTPUT_DIR / "resultado_nts.xlsx"

def run():
    nts = discover_nts_by_publish_date()
    if not nts:
        log.info("Nenhuma regra coletada. Ainda assim gerando planilha com cabeçalhos.")
        df = pd.DataFrame(columns=[
            "NT","Versão","Publicada em","Implantação Homologação","Implantação Produção",
            "Grupo","Campo","Regra","Aplic.","Msg","Descrição"
        ])
        df.to_excel(OUTPUT_XLSX, index=False)
        log.info("Planilha gerada: %s", OUTPUT_XLSX)
        log.info("Novas regras coletadas nesta execução: 0")
        return

    all_rows: List[dict] = []
    total_rules = 0

    for nt in nts:
        pdf = ensure_pdf_downloaded(nt)
        publicada_em = nt.publicada_em.strftime("%d/%m/%Y") if nt.publicada_em else None

        if not pdf:
            # gera linha “vazia” com metadados, para ainda constar na planilha
            row = NTRow(
                nt_titulo=nt.titulo, nt_versao=None, publicada_em=publicada_em,
                implantacao_homolog=None, implantacao_producao=None,
                grupo=None, campo=None, regra=None, aplic=None, msg=None, descricao=None
            )
            all_rows.append({
                "NT": row.nt_titulo,
                "Versão": row.nt_versao,
                "Publicada em": row.publicada_em,
                "Implantação Homologação": row.implantacao_homolog,
                "Implantação Produção": row.implantacao_producao,
                "Grupo": row.grupo,
                "Campo": row.campo,
                "Regra": row.regra,
                "Aplic.": row.aplic,
                "Msg": row.msg,
                "Descrição": row.descricao,
            })
            continue

        try:
            rows = extract_rules_from_pdf(pdf, nt_titulo=nt.titulo, publicada_em=publicada_em)
        except Exception as e:
            log.error("Erro extraindo regras de %s\n%s", pdf, e, exc_info=False)
            # Linha de metadados mesmo assim
            row = NTRow(
                nt_titulo=nt.titulo, nt_versao=None, publicada_em=publicada_em,
                implantacao_homolog=None, implantacao_producao=None,
                grupo=None, campo=None, regra=None, aplic=None, msg=None, descricao=None
            )
            rows = [row]

        # acumula
        for r in rows:
            all_rows.append({
                "NT": r.nt_titulo,
                "Versão": r.nt_versao,
                "Publicada em": r.publicada_em,
                "Implantação Homologação": r.implantacao_homolog,
                "Implantação Produção": r.implantacao_producao,
                "Grupo": r.grupo,
                "Campo": r.campo,
                "Regra": r.regra,
                "Aplic.": r.aplic,
                "Msg": r.msg,
                "Descrição": r.descricao,
            })

        # contabiliza quantas realmente tinham regra (com descrição)
        total_rules += sum(1 for r in rows if r.descricao)

    out = write_rules_to_xlsx(all_rows, OUTPUT_XLSX)
    log.info("Planilha gerada: %s", out)
    log.info("Novas regras coletadas nesta execução: %d", total_rules)

if __name__ == "__main__":
    run()
