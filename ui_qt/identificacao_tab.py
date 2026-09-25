"""Aba Identificação (Qt) — equivalente a ui/aba_identificacao.py.

Diferente da versão Streamlit: aqui é um QWidget que fica vivo o tempo
todo (não recriado a cada interação), então não existe o problema de
"session_state apagado ao trocar de aba" que exigiu reforço de cache do
lado do Streamlit — o próprio widget é o estado.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.models import Identificacao
from core.parsing import formatar_cpf_cnpj
from ui_qt.tema_qt import MAX_ITENS_VISIVEIS_COMBO, Papel, titulo_secao


def _combo(itens: list[str]) -> QComboBox:
    caixa = QComboBox()
    caixa.addItems(itens)
    caixa.setMaxVisibleItems(MAX_ITENS_VISIVEIS_COMBO)
    # mesmo motivo de ui_qt/perimetro_tab.py::_combo — domínio de opções
    # curtas deixava a caixa estreita e "embolada" (texto/seta espremidos).
    caixa.setMinimumContentsLength(12)
    caixa.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    return caixa


class _CampoCpfCnpj(QLineEdit):
    """Mascara progressiva: só dígitos entram, o programa monta pontos/
    barra/traço sozinho — colar de fora com pontuação já formatada também
    funciona (formatar_cpf_cnpj extrai só os dígitos primeiro)."""

    def __init__(self) -> None:
        super().__init__()
        self.setMaxLength(18)  # CNPJ formatado: 00.000.000/0000-00
        self.textEdited.connect(self._reformatar)

    def _reformatar(self, texto: str) -> None:
        posicao_cursor = self.cursorPosition()
        digitos_antes = sum(c.isdigit() for c in texto[:posicao_cursor])
        formatado = formatar_cpf_cnpj(texto)

        nova_posicao = len(formatado)
        contados = 0
        for i, c in enumerate(formatado):
            if contados >= digitos_antes:
                nova_posicao = i
                break
            if c.isdigit():
                contados += 1

        self.blockSignals(True)
        self.setText(formatado)
        self.setCursorPosition(nova_posicao)
        self.blockSignals(False)


def _combo_pesquisavel(itens: list[str]) -> QComboBox:
    """Município tem 5571 opções — rolar essa lista não é viável. Editável
    + QCompleter com filtro "contém" (não só "começa com") deixa digitar
    parte do nome pra filtrar, sem precisar de biblioteca externa."""
    caixa = QComboBox()
    caixa.addItems(itens)
    caixa.setEditable(True)
    caixa.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    completador = QCompleter(itens, caixa)
    completador.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completador.setFilterMode(Qt.MatchFlag.MatchContains)
    completador.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    caixa.setCompleter(completador)
    return caixa


class AbaIdentificacao(QWidget):
    def __init__(self, dominios: dict, municipios: list[str], tema: dict[str, Papel]) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        layout.addWidget(
            titulo_secao("Identificação do Serviço de Georreferenciamento", tema["servico_titulo"])
        )
        form_servico = QFormLayout()
        self.natureza_servico = _combo(dominios["natureza_servico"])
        form_servico.addRow("Natureza do serviço", self.natureza_servico)
        layout.addLayout(form_servico)

        layout.addWidget(titulo_secao("Identificação do Detentor", tema["detentor_titulo"]))
        self.tipo_pessoa = _combo(dominios["tipo_pessoa"])
        self.cpf_cnpj = _CampoCpfCnpj()
        self.nome = QLineEdit()
        linha_detentor = QHBoxLayout()
        linha_detentor.addLayout(_form("Tipo pessoa", self.tipo_pessoa), 1)
        linha_detentor.addLayout(_form("CPF/CNPJ", self.cpf_cnpj), 1)
        linha_detentor.addLayout(_form("Nome", self.nome), 2)
        layout.addLayout(linha_detentor)

        layout.addWidget(titulo_secao("Identificação da Área", tema["area_titulo"]))
        self.denominacao_area = QLineEdit()
        layout.addLayout(_form("Denominação da área", self.denominacao_area))

        self.situacao = _combo(dominios["situacao"])
        self.natureza_area = _combo(dominios["natureza_area"])
        self.codigo_imovel_sncr = QLineEdit()
        linha2 = QHBoxLayout()
        linha2.addLayout(_form("Situação", self.situacao), 1)
        linha2.addLayout(_form("Natureza da área", self.natureza_area), 1)
        linha2.addLayout(_form("Código do Imóvel (SNCR/INCRA)", self.codigo_imovel_sncr), 1)
        layout.addLayout(linha2)

        self.codigo_cartorio_cns = QLineEdit()
        self.matricula = QLineEdit()
        self.municipio_1 = _combo_pesquisavel([""] + municipios)
        linha3 = QHBoxLayout()
        linha3.addLayout(_form("Código do cartório (CNS)", self.codigo_cartorio_cns), 1)
        linha3.addLayout(_form("Matrícula", self.matricula), 1)
        linha3.addLayout(_form("Município", self.municipio_1), 1)
        layout.addLayout(linha3)

        layout.addStretch()

    def modelo(self) -> Identificacao:
        return Identificacao(
            natureza_servico=self.natureza_servico.currentText(),
            tipo_pessoa=self.tipo_pessoa.currentText(),
            nome=self.nome.text(),
            cpf_cnpj=self.cpf_cnpj.text(),
            denominacao_area=self.denominacao_area.text(),
            situacao=self.situacao.currentText(),
            natureza_area=self.natureza_area.currentText(),
            codigo_imovel_sncr=self.codigo_imovel_sncr.text(),
            codigo_cartorio_cns=self.codigo_cartorio_cns.text(),
            matricula=self.matricula.text(),
            municipio_1=self.municipio_1.currentText(),
        )

    def carregar(self, dados: Identificacao) -> None:
        self.natureza_servico.setCurrentText(dados.natureza_servico)
        self.tipo_pessoa.setCurrentText(dados.tipo_pessoa)
        self.nome.setText(dados.nome)
        self.cpf_cnpj.setText(formatar_cpf_cnpj(dados.cpf_cnpj))
        self.denominacao_area.setText(dados.denominacao_area)
        self.situacao.setCurrentText(dados.situacao)
        self.natureza_area.setCurrentText(dados.natureza_area)
        self.codigo_imovel_sncr.setText(dados.codigo_imovel_sncr)
        self.codigo_cartorio_cns.setText(dados.codigo_cartorio_cns)
        self.matricula.setText(dados.matricula)
        self.municipio_1.setCurrentText(dados.municipio_1)


def _form(rotulo: str, campo: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.addWidget(QLabel(rotulo))
    layout.addWidget(campo)
    return layout
