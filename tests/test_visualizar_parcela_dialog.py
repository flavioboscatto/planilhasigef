"""Testes de ui_qt/visualizar_parcela_dialog.py (V3): desenha vértices +
polilinha fechada da parcela, destacando lados que se cruzam."""
from __future__ import annotations

from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem

from core.models import Vertice
from ui_qt.visualizar_parcela_dialog import VisualizarParcelaDialog, _COR_CRUZAMENTO, _COR_LADO


def _v(codigo: str, e_long: float, n_lat: float) -> Vertice:
    return Vertice(codigo=codigo, e_long=e_long, n_lat=n_lat)


_TRIANGULO = [_v("A", -48.0, -9.0), _v("B", -47.9, -9.1), _v("C", -48.1, -9.1)]

_BORBOLETA = [
    _v("A", -48.0, -9.0),
    _v("B", -47.9, -9.1),
    _v("C", -47.9, -9.0),
    _v("D", -48.0, -9.1),
]


def test_poligono_simples_mostra_mensagem_sem_cruzamento(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    assert "sem autointerseção" in dialogo.rotulo_resultado.text()
    linhas = [i for i in dialogo.cena.items() if isinstance(i, QGraphicsLineItem)]
    pontos = [i for i in dialogo.cena.items() if isinstance(i, QGraphicsEllipseItem)]
    rotulos = [i for i in dialogo.cena.items() if isinstance(i, QGraphicsTextItem)]
    assert len(linhas) == 3
    assert len(pontos) == 3
    assert len(rotulos) == 3
    assert all(item.pen().color() == _COR_LADO for item in linhas)


def test_poligono_com_cruzamento_avisa_e_destaca_o_lado_em_vermelho(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _BORBOLETA, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    assert "autointerseção" in dialogo.rotulo_resultado.text()
    assert "A" in dialogo.rotulo_resultado.text() and "C" in dialogo.rotulo_resultado.text()
    linhas = [i for i in dialogo.cena.items() if isinstance(i, QGraphicsLineItem)]
    cores = {item.pen().color().name() for item in linhas}
    assert _COR_CRUZAMENTO.name() in cores
    assert _COR_LADO.name() in cores


def test_menos_de_3_vertices_avisa_sem_desenhar(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: [_v("A", -48.0, -9.0)], -51.0, "Sul")
    qtbot.addWidget(dialogo)

    assert "pelo menos 3" in dialogo.rotulo_resultado.text()
    assert len(dialogo.cena.items()) == 0


def test_botao_atualizar_redesenha_com_dados_novos(qtbot):
    vertices_atuais = {"lista": _TRIANGULO}
    dialogo = VisualizarParcelaDialog(lambda: vertices_atuais["lista"], -51.0, "Sul")
    qtbot.addWidget(dialogo)
    assert len([i for i in dialogo.cena.items() if isinstance(i, QGraphicsEllipseItem)]) == 3

    vertices_atuais["lista"] = _BORBOLETA
    dialogo._desenhar()

    assert len([i for i in dialogo.cena.items() if isinstance(i, QGraphicsEllipseItem)]) == 4
    assert "autointerseção" in dialogo.rotulo_resultado.text()
