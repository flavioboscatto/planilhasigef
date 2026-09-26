"""Monta/aplica o projeto inteiro (.sigefproj) a partir da/para a janela
Qt — equivalente a ui/projeto.py (Streamlit), bem mais simples aqui porque
os widgets Qt já SÃO o estado (ficam vivos o tempo todo): não existe o
problema de "session_state apagado ao trocar de aba" que exigia cache e
reserva na versão Streamlit — só ler direto de cada aba/painel.

Funções livres (não métodos de JanelaPrincipal) pra não precisar importar
app_qt aqui — `janela` só precisa ter os atributos/métodos usados abaixo
(aba_identificacao, _abas_perimetro(), painel_numeracao, nome_projeto).
"""
from __future__ import annotations

import pandas as pd

from core.models import Identificacao, Perimetro
from core.tabela_vertices import COLUNAS_VERTICE


def _serializar_importacoes(aba) -> list[dict]:
    """Cada sub-aba "Importação N" (ui_qt/importacao_tab.py::AbaImportacao)
    também entra no .sigefproj — sem isto, fechar e reabrir o projeto
    perdia a conferência do que foi importado e a possibilidade de
    recalcular geodésica de novo depois."""
    importacoes = []
    for i in range(1, aba.subabas.count()):
        sub = aba.subabas.widget(i)
        dados_utm_brutos = sub._dados_utm_brutos
        dados_geodesica_original = sub._dados_geodesica_original
        importacoes.append({
            "colunas": sub._colunas,
            "linhas": sub._dataframe_atual().to_dict(orient="records"),
            "dados_utm_brutos": dados_utm_brutos.to_dict(orient="records") if dados_utm_brutos is not None else None,
            "dados_geodesica_original": (
                dados_geodesica_original.to_dict(orient="records") if dados_geodesica_original is not None else None
            ),
            "meridiano": float(sub.combo_meridiano.currentText()) if hasattr(sub, "combo_meridiano") else None,
            "hemisferio": sub.combo_hemisferio.currentText() if hasattr(sub, "combo_hemisferio") else None,
        })
    return importacoes


def montar_projeto(janela) -> dict:
    identificacao = janela.aba_identificacao.modelo().model_dump()

    abas = janela._abas_perimetro()
    parcelas = []
    for aba in abas:
        campos = aba.modelo().model_dump(exclude={"vertices"})
        campos["vertices"] = aba.modelo_tabela.dataframe().to_dict(orient="records")
        campos["importacoes"] = _serializar_importacoes(aba)
        # rótulo da aba (V4, renomeável pelo usuário) — separado dos campos
        # do modelo (Denominação/Parcela número), que são conteúdo da
        # planilha; isto aqui é só o texto da aba na tela.
        campos["nome_aba"] = janela.abas.tabText(janela.abas.indexOf(aba))
        # qual sub-aba (Tabela de Perímetro/Importação N) estava aberta —
        # sem isto, reabrir o projeto sempre pousava na última sub-aba
        # criada (efeito colateral de _criar_aba_importacao, que muda o
        # foco pra cada importação recriada durante o carregamento).
        campos["subaba_atual"] = aba.subabas.currentIndex()
        parcelas.append(campos)

    # índice 0 é sempre a aba Identificação — -1 pra guardar a posição
    # relativa entre as abas de parcela (0 = Parcela 1), pelo mesmo motivo
    # de subaba_atual acima (_adicionar_aba_parcela também rouba o foco a
    # cada parcela recriada).
    parcela_atual = max(0, janela.abas.currentIndex() - 1)

    painel = janela.painel_numeracao
    numeracao = {
        "codigo_credenciado": painel.campo_credenciado.text(),
        "formato": painel.combo_formato.currentText(),
        "inicio_por_tipo": {codigo: campo.text() for codigo, campo in painel._campos_numero.items()},
    }

    return {
        "nome_projeto": getattr(janela, "nome_projeto", ""),
        "identificacao": identificacao,
        "num_parcelas": len(abas),
        "parcelas": parcelas,
        "numeracao": numeracao,
        "parcela_atual": parcela_atual,
    }


def aplicar_projeto(janela, dados: dict) -> None:
    janela.aba_identificacao.carregar(Identificacao(**dados.get("identificacao", {})))

    # remove todas as abas de parcela existentes e recria do zero — mais
    # simples e robusto que tentar casar índice a índice com o que já
    # estava aberto (e igual em custo, já que Qt não perde nada ao
    # recriar: o dado vem todo do arquivo mesmo).
    while janela.abas.count() > 1:
        widget = janela.abas.widget(1)
        janela.abas.removeTab(1)
        widget.deleteLater()
    janela._proxima_parcela = 1

    parcelas_dados = dados.get("parcelas", [])
    quantidade = max(1, dados.get("num_parcelas", len(parcelas_dados) or 1))
    base_perimetro = Perimetro().model_dump(exclude={"vertices"})

    for i in range(quantidade):
        janela._adicionar_aba_parcela()
        aba = janela._abas_perimetro()[-1]
        parcela_dados = parcelas_dados[i] if i < len(parcelas_dados) else {}

        valores = {
            **base_perimetro,
            **{k: v for k, v in parcela_dados.items() if k not in ("vertices", "importacoes") and v is not None},
        }
        aba.carregar_cabecalho(Perimetro(vertices=[], **valores))

        # ausente = arquivo salvo antes do V4 (renomear aba) — mantém o
        # rótulo padrão que _adicionar_aba_parcela já deu.
        nome_aba = parcela_dados.get("nome_aba")
        if nome_aba:
            janela.abas.setTabText(janela.abas.indexOf(aba), nome_aba)

        tabela = pd.DataFrame(parcela_dados.get("vertices", []), columns=COLUNAS_VERTICE)
        aba.modelo_tabela.substituir(tabela)

        for importacao in parcela_dados.get("importacoes", []):
            # nome diferente do parâmetro "dados" da função de propósito: um
            # DataFrame também tem `.get()` (procura coluna, não chave) —
            # sobrescrever "dados" aqui fazia `dados.get("numeracao", {})",
            # já perto do fim da função, devolver "{}" sempre em silêncio
            # (nunca um erro) sempre que alguma parcela tivesse importação.
            dados_importados = pd.DataFrame(importacao.get("linhas", []), columns=importacao.get("colunas", []))
            utm_brutos = importacao.get("dados_utm_brutos")
            dados_utm_brutos = pd.DataFrame(utm_brutos, columns=["e_long", "n_lat"]) if utm_brutos else None
            # ausente = arquivo salvo antes do V6 (colunas de referência do
            # formato original na importação) — mantém compatível.
            geo_original = importacao.get("dados_geodesica_original")
            dados_geodesica_original = pd.DataFrame(geo_original, columns=["e_long", "n_lat"]) if geo_original else None
            aba._criar_aba_importacao(
                dados_importados, dados_utm_brutos, dados_geodesica_original,
                importacao.get("meridiano") or 0.0, importacao.get("hemisferio") or "",
            )

        # sem isto, a aba fica na última sub-aba de importação recriada
        # acima (_criar_aba_importacao muda o foco pra cada uma) — padrão
        # 0 = Tabela de Perímetro, mesmo numa parcela sem "subaba_atual"
        # salva (arquivo de versão anterior a este campo existir).
        indice_subaba = min(max(0, parcela_dados.get("subaba_atual", 0)), aba.subabas.count() - 1)
        aba.subabas.setCurrentIndex(indice_subaba)

    # mesmo motivo, um nível acima: sem isto a janela fica na última
    # parcela recriada (_adicionar_aba_parcela muda o foco a cada uma).
    indice_parcela = min(max(0, dados.get("parcela_atual", 0)), quantidade - 1)
    janela.abas.setCurrentIndex(1 + indice_parcela)

    numeracao = dados.get("numeracao", {})
    painel = janela.painel_numeracao
    painel.campo_credenciado.setText(numeracao.get("codigo_credenciado", ""))
    painel.combo_formato.setCurrentText(numeracao.get("formato", "001"))
    for codigo, valor in numeracao.get("inicio_por_tipo", {}).items():
        if codigo in painel._campos_numero:
            painel._campos_numero[codigo].setText(str(valor))

    janela.nome_projeto = dados.get("nome_projeto", "")
