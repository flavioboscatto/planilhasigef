"""Fusão de dados importados na tabela de vértices, casando pelo código
(chave da importação — nem sempre vem tudo no mesmo arquivo: pode ser só
coordenadas numa importação e só precisões noutra).

Regra: um campo do arquivo importado sempre sobrescreve o que já está na
tabela para aquele código — mas só os campos presentes e não vazios no
arquivo; uma coluna que o arquivo nem tem (ex.: sigma, numa importação só
de coordenadas) não apaga o que já estava preenchido. Código que ainda
não existe na tabela vira linha nova — sem limite de quantidade: o
gravador (core/ods_writer.py) insere linha na planilha final conforme
precisar, então a importação nunca precisa descartar vértice por falta de
espaço.
"""
from __future__ import annotations

import pandas as pd


def mesclar_por_codigo(
    tabela_atual: pd.DataFrame, dados_importados: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    """`dados_importados` já vem no schema de vértice (colunas renomeadas
    pela correlação da UI) e precisa ter a coluna 'codigo'."""
    avisos: list[str] = []
    tabela = tabela_atual.copy()
    tabela["codigo"] = tabela["codigo"].astype(str)
    # linha sem código é vaga vazia (grade nova, sem vértice de verdade —
    # mesmo critério de _preenchido em ui/aba_perimetro.py), não vértice de
    # verdade ocupando espaço: a importação reaproveita essas vagas antes
    # de criar linha nova, em vez de deixá-las paradas no meio da tabela.
    vagas_livres = [idx for idx in tabela.index if tabela.at[idx, "codigo"].strip() == ""]
    novas_linhas = []

    for _, linha_nova in dados_importados.iterrows():
        codigo = str(linha_nova.get("codigo", "")).strip()
        if not codigo:
            continue
        indices_existentes = tabela.index[tabela["codigo"] == codigo].tolist()
        if indices_existentes:
            idx = indices_existentes[0]
            for campo, valor in linha_nova.items():
                if campo == "codigo" or str(valor).strip() == "":
                    continue
                tabela.loc[idx, campo] = valor
        elif vagas_livres:
            idx = vagas_livres.pop(0)
            if "renumerar" in tabela.columns:
                tabela.loc[idx, "renumerar"] = False
            for campo, valor in linha_nova.items():
                if str(valor).strip() == "":
                    continue
                tabela.loc[idx, campo] = valor
        else:
            # "renumerar" nasce desmarcado pra vértice vindo de arquivo: pode
            # ser um vértice de outro credenciado, que a ferramenta de
            # renumeração (core/numeracao.py) não deve tocar sem o
            # profissional marcar de propósito. "" quebraria a coluna, que
            # é booleana (CheckboxColumn).
            nova_linha = {c: (False if c == "renumerar" else "") for c in tabela.columns}
            nova_linha.update(
                {k: v for k, v in linha_nova.items() if str(v).strip() != ""}
            )
            novas_linhas.append(nova_linha)

    if novas_linhas:
        tabela = pd.concat([tabela, pd.DataFrame(novas_linhas)], ignore_index=True)
    return tabela, avisos
