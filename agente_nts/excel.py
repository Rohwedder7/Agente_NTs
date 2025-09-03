from __future__ import annotations
from pathlib import Path
import pandas as pd
from .utils import ensure_excel_path

COLUMNS = [
    "NT",
    "Versão",
    "Publicada em",
    "Implantação Homologação",
    "Implantação Produção",
    "Grupo",
    "Campo",
    "Regra",
    "Aplic.",
    "Msg",
    "Descrição",
]

def write_rules_to_xlsx(rows: list, out_path: Path) -> Path:
    out_path = ensure_excel_path(out_path)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(out_path, index=False)
    return out_path
