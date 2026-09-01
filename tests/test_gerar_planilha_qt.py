"""Teste da Fase 8 (gerar planilha SIGEF): fluxo completo preencher ->
menu Gerar -> escolher onde salvar (QFileDialog nativo simulado) -> .ods
válido no disco, reaproveitando core/ods_writer.py sem mudança nenhuma."""
from __future__ import annotations

import zipfile

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app_qt import JanelaPrincipal


def test_gerar_planilha_produz_ods_valido_no_caminho_escolhido(qtbot, tmp_path, monkeypatch):
    # QMessageBox.information (aviso de sucesso) é modal — sem stub, o
    # teste travaria esperando clique.
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: None)

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela.aba_identificacao.nome.setText("Fulano de Tal")
    janela.aba_identificacao.cpf_cnpj.setText("123.456.789-00")
    aba = janela._abas_perimetro()[0]
    colunas = aba.modelo_tabela.dataframe().columns
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, colunas.get_loc("codigo")), "AJ4-M-001", Qt.ItemDataRole.EditRole)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, colunas.get_loc("e_long")), "-48,50", Qt.ItemDataRole.EditRole)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, colunas.get_loc("n_lat")), "-27,50", Qt.ItemDataRole.EditRole)

    caminho = tmp_path / "saida.ods"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(caminho), "")))

    janela._gerar_planilha()

    assert caminho.exists()
    assert caminho.stat().st_size > 0
    with zipfile.ZipFile(caminho) as z:
        assert "content.xml" in z.namelist()
        conteudo = z.read("content.xml").decode("utf-8")
        assert "AJ4-M-001" in conteudo
