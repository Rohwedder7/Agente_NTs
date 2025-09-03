# Agente de NTs — Extração de Regras de Validação (NF-e/NFC-e)

Este agente em **Python** visita páginas oficiais de Notas Técnicas (NTs), baixa os **PDFs**, extrai **Regras de Validação** e **prazos** de **Homologação/Produção**, e gera um **Excel** com as colunas:

- `NT`
- `regra_de_validacao`
- `descricao_da_regra`
- `codigo_do_erro`
- `mensagem_de_erro`
- `data_homologacao`
- `data_producao`

## Como rodar localmente (VS Code)

1. Crie (opcional) um ambiente virtual e ative.
2. Instale dependências: `pip install -r requirements.txt`
3. Rode: `python -m src.main`
4. Abra `output/resultado_nts.xlsx`

## Agendamento (GitHub Actions)
Workflow em `.github/workflows/weekly.yml` agenda 1x por semana; faz upload do Excel como artifact e, opcionalmente, commita no repositório se `PUSH_RESULTS=true` (Actions → Variables).

## Estrutura
```
agent_nts/
├── .github/workflows/weekly.yml
├── config.yaml
├── data/pdfs/
├── output/
├── requirements.txt
└── src/
    ├── excel_writer.py
    ├── fetch_nts.py
    ├── main.py
    ├── parse_nt_pdf.py
    └── utils.py
```
