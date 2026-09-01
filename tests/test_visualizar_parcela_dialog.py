"""Testes de ui_qt/visualizar_parcela_dialog.py (V3): desenha vértices +
polilinha fechada da parcela, destacando lados que se cruzam, mostra a
área SGL/INCRA (core/sgl.py) e permite zoom (scroll) e pan (arraste)."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsTextItem,
    QGraphicsView,
)

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


def test_area_sgl_e_mostrada_para_poligono_simples(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    assert "Área" in dialogo.rotulo_area.text()
    assert "ha" in dialogo.rotulo_area.text()


def test_area_nao_e_calculada_quando_ha_cruzamento(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _BORBOLETA, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    assert "não calculada" in dialogo.rotulo_area.text()
    assert "cruzam" in dialogo.rotulo_area.text()


def test_scroll_do_mouse_da_zoom_na_visualizacao(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")
    qtbot.addWidget(dialogo)
    escala_antes = dialogo.view.transform().m11()

    evento = QWheelEvent(
        QPointF(0, 0), QPointF(0, 0), QPoint(0, 0), QPoint(0, 120),
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase, False,
    )
    dialogo.view.wheelEvent(evento)

    assert dialogo.view.transform().m11() > escala_antes


def test_arrastar_com_botao_esquerdo_move_o_desenho():
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")

    assert dialogo.view.dragMode() == QGraphicsView.DragMode.ScrollHandDrag


def test_cena_tem_espaco_extra_pra_navegar_alem_do_desenho(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    cena_rect = dialogo.cena.sceneRect()
    itens_rect = dialogo.cena.itemsBoundingRect()

    assert cena_rect.width() > itens_rect.width()
    assert cena_rect.height() > itens_rect.height()
    assert cena_rect.left() < itens_rect.left()
    assert cena_rect.top() < itens_rect.top()
    assert cena_rect.right() > itens_rect.right()
    assert cena_rect.bottom() > itens_rect.bottom()


def test_rotulo_do_vertice_tem_tamanho_fixo_e_ignora_zoom(qtbot):
    dialogo = VisualizarParcelaDialog(lambda: _TRIANGULO, -51.0, "Sul")
    qtbot.addWidget(dialogo)

    rotulos = [i for i in dialogo.cena.items() if isinstance(i, QGraphicsTextItem)]
    assert rotulos
    for rotulo in rotulos:
        assert rotulo.font().pointSize() == 12
        assert rotulo.flags() & QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
