"""Diálogo "Visualizar parcela" (Qt) — desenha os vértices (com código) e
a polilinha fechada do perímetro, num QGraphicsView nativo. Sem
matplotlib: o projeto exclui essa lib de propósito do empacotamento
(sigef_qt.spec) e o app nunca desenhou gráfico até agora (V3, primeira
vez).

Não-modal, mesmo molde de ui_qt/importar_vertices_dialog.py: quem abre
guarda a referência em atributo de instância (senão o Python coleta o
objeto e a janela some sozinha) — ver ui_qt/perimetro_tab.py::_abrir_visualizacao.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.geo import geodesica_para_utm
from core.models import Vertice
from core.validators.geometria import verificar_autointersecao

_RAIO_PONTO = 4
_COR_LADO = QColor("#345b3a")  # mesmo verde escuro de "perimetro_titulo" (config/theme_tokens.json)
_COR_CRUZAMENTO = QColor("#b3261e")
_COR_PONTO = QColor("#000000")
_MARGEM_PX = 40
_LARGURA_CENA = 700
_ALTURA_CENA = 600


class VisualizarParcelaDialog(QDialog):
    def __init__(
        self,
        obter_vertices: Callable[[], list[Vertice]],
        meridiano_central: float,
        hemisferio: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Visualizar parcela")
        self.resize(760, 700)
        self._obter_vertices = obter_vertices
        self._meridiano_central = meridiano_central
        self._hemisferio = hemisferio

        layout = QVBoxLayout(self)

        self.rotulo_resultado = QLabel()
        self.rotulo_resultado.setWordWrap(True)
        layout.addWidget(self.rotulo_resultado)

        self.cena = QGraphicsScene(0, 0, _LARGURA_CENA, _ALTURA_CENA)
        self.view = QGraphicsView(self.cena)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view, 1)

        # cobre o caso de editar a grade com este diálogo ainda aberto —
        # sem precisar fechar/reabrir pra ver o resultado atualizado.
        btn_atualizar = QPushButton("Atualizar")
        btn_atualizar.clicked.connect(self._desenhar)
        layout.addWidget(btn_atualizar)

        self._desenhar()

    def _desenhar(self) -> None:
        self.cena.clear()
        vertices = self._obter_vertices()

        if len(vertices) < 3:
            self.rotulo_resultado.setText(
                "É preciso pelo menos 3 vértices com código preenchido para desenhar o perímetro."
            )
            return

        cruzamentos = verificar_autointersecao(vertices)
        if cruzamentos:
            mensagens = "\n".join(c.mensagem for c in cruzamentos)
            self.rotulo_resultado.setText(f"Perímetro com autointerseção:\n{mensagens}")
        else:
            self.rotulo_resultado.setText("Perímetro sem autointerseção.")
        lados_com_problema = {c.indice_a for c in cruzamentos} | {c.indice_b for c in cruzamentos}

        # metros de verdade (não grau cru): grau de longitude "encolhe" por
        # cos(latitude) em relação a grau de latitude — desenhar direto em
        # grau distorceria a forma do polígono (core/geo.py).
        pontos_m = [
            geodesica_para_utm(v.e_long, v.n_lat, self._meridiano_central, self._hemisferio) for v in vertices
        ]
        self._desenhar_pontos(vertices, pontos_m, lados_com_problema)

    def _desenhar_pontos(
        self, vertices: list[Vertice], pontos_m: list[tuple[float, float]], lados_com_problema: set[int]
    ) -> None:
        xs = [p[0] for p in pontos_m]
        ys = [p[1] for p in pontos_m]
        largura_m = max(xs) - min(xs) or 1.0
        altura_m = max(ys) - min(ys) or 1.0
        # escala uniforme nos dois eixos — senão a forma do polígono fica
        # distorcida (um retângulo pareceria um quadrado, por exemplo).
        escala = min(
            (_LARGURA_CENA - 2 * _MARGEM_PX) / largura_m,
            (_ALTURA_CENA - 2 * _MARGEM_PX) / altura_m,
        )

        def _para_cena(easting: float, northing: float) -> QPointF:
            x = _MARGEM_PX + (easting - min(xs)) * escala
            # eixo Y invertido: northing cresce pra cima, QGraphicsScene
            # cresce pra baixo.
            y = _MARGEM_PX + (max(ys) - northing) * escala
            return QPointF(x, y)

        pontos_cena = [_para_cena(e, n) for e, n in pontos_m]
        n = len(vertices)

        for i in range(n):
            p1 = pontos_cena[i]
            p2 = pontos_cena[(i + 1) % n]
            cor = _COR_CRUZAMENTO if i in lados_com_problema else _COR_LADO
            largura_linha = 2.5 if i in lados_com_problema else 1.5
            linha = QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y())
            linha.setPen(QPen(cor, largura_linha))
            self.cena.addItem(linha)

        for vertice, ponto in zip(vertices, pontos_cena):
            circulo = QGraphicsEllipseItem(
                QRectF(ponto.x() - _RAIO_PONTO, ponto.y() - _RAIO_PONTO, 2 * _RAIO_PONTO, 2 * _RAIO_PONTO)
            )
            circulo.setBrush(QBrush(_COR_PONTO))
            circulo.setPen(QPen(_COR_PONTO))
            self.cena.addItem(circulo)

            rotulo = QGraphicsTextItem(vertice.codigo)
            rotulo.setPos(ponto.x() + _RAIO_PONTO + 2, ponto.y() - 10)
            self.cena.addItem(rotulo)
