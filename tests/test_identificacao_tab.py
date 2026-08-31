"""Testes da Fase 2 (aba Identificação): campos existem, capturam valor
digitado/selecionado, e `carregar()` repopula tudo (usado na Fase 7 pelo
Abrir projeto)."""
from __future__ import annotations

import json
from pathlib import Path

from core.models import Identificacao
from ui_qt.identificacao_tab import AbaIdentificacao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _carregar_json(nome):
    with (CONFIG_DIR / nome).open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba() -> AbaIdentificacao:
    dominios = _carregar_json("dominios.json")
    municipios = _carregar_json("municipios.json")
    tema = carregar_tema()
    return AbaIdentificacao(dominios, municipios, tema)


def test_modelo_inicial_bate_com_primeira_opcao_dos_combos(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    modelo = aba.modelo()
    assert modelo.natureza_servico == "Particular"
    assert modelo.tipo_pessoa == "Física"
    assert modelo.nome == ""
    assert modelo.municipio_1 == ""


def test_digitar_e_selecionar_reflete_no_modelo(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba.nome.setText("Fulano de Tal")
    aba.cpf_cnpj.setText("123.456.789-00")
    aba.denominacao_area.setText("Fazenda Teste")
    aba.matricula.setText("12345")
    aba.tipo_pessoa.setCurrentText("Jurídica")

    modelo = aba.modelo()
    assert modelo.nome == "Fulano de Tal"
    assert modelo.cpf_cnpj == "123.456.789-00"
    assert modelo.denominacao_area == "Fazenda Teste"
    assert modelo.matricula == "12345"
    assert modelo.tipo_pessoa == "Jurídica"


def test_carregar_repopula_todos_os_campos(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    dados = Identificacao(
        natureza_servico="Contrato com Administração Pública",
        tipo_pessoa="Jurídica",
        nome="Ciclano da Silva",
        cpf_cnpj="11.222.333/0001-44",
        denominacao_area="Sítio Bom Retiro",
        situacao="Área Titulada não Registrada",
        natureza_area="Terra Indígena",
        codigo_imovel_sncr="SNCR-1",
        codigo_cartorio_cns="CNS-9",
        matricula="999",
        municipio_1="Abadia de Goiás-GO",
        municipio_2="",
    )
    aba.carregar(dados)

    modelo = aba.modelo()
    assert modelo == dados


def test_municipio_completer_filtra_por_conteudo_nao_so_prefixo(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    completador = aba.municipio_1.completer()
    completador.setCompletionPrefix("Goi")
    resultados = [completador.completionModel().data(completador.completionModel().index(i, 0))
                  for i in range(completador.completionCount())]
    assert any("Goi" in r for r in resultados)
