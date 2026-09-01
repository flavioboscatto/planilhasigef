"""Recolhe os dados ao vivo das abas de Parcela (e suas sub-abas
"Importação N") pra montar o Relatório em DOCX (core/relatorio_docx.py) —
mesmo espírito de ui_qt/projeto_qt.py::montar_projeto, mas só o que o
relatório precisa (sem meridiano/hemisfério/dados brutos de UTM, que só
servem pra recalcular geodésica depois).
"""
from __future__ import annotations


def montar_dados_relatorio(janela) -> list[dict]:
    parcelas = []
    for aba in janela._abas_perimetro():
        importacoes = []
        for i in range(1, aba.subabas.count()):
            sub = aba.subabas.widget(i)
            importacoes.append(
                {
                    "titulo": aba.subabas.tabText(i),
                    "colunas": sub._colunas,
                    "linhas": sub._dataframe_atual().to_dict(orient="records"),
                }
            )
        parcelas.append({"perimetro": aba.modelo(), "importacoes": importacoes})
    return parcelas
