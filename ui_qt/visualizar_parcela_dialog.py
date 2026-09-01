"""Diálogo "Visualizar parcela" (Qt) — desenha os vértices (com código) e
a polilinha fechada do perímetro, num QGraphicsView nativo. Sem
matplotlib: o projeto exclui essa lib de propósito do empacotamento
(sigef_qt.spec) e o app nunca desenhou gráfico até agora (V3, primeira
vez).

Também mostra a área da parcela pelo Sistema Geodésico Local do INCRA
(core/sgl.py) — só quando o perímetro não tem autointerseção (reaproveita
a mesma checagem usada pra colorir os lados problemáticos).

Não-modal, mesmo molde de ui_qt/importar_vertices_dialog.py: quem abre
guarda a referência em atributo de instância (senão o Python coleta o
objeto e a janela some sozinha) — ver ui_qt/perimetro_tab.py::_abrir_visualizacao.
"""
from __future__ import annotations

import warnings
from typing import Callable

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
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
from core.sgl import area_sgl
from core.validators.geometria import verificar_autointersecao

_RAIO_PONTO = 4
_COR_LADO = QColor("#345b3a")  # mesmo verde escuro de "perimetro_titulo" (config/theme_tokens.json)
_COR_CRUZAMENTO = QColor("#b3261e")
_COR_PONTO = QColor("#000000")
_MARGEM_PX = 40
_LARGURA_CENA = 700
_ALTURA_CENA = 600
_FATOR_ZOOM = 1.15
_ZOOM_MINIMO = 0.2
_ZOOM_MAXIMO = 15.0
_OFFSET_NAVEGACAO_M = 30.0  # pedido do usuário: espaço extra pra navegar em volta do desenho
_TAMANHO_ROTULO_PT = 12


class _VisualizacaoView(QGraphicsView):
    """QGraphicsView + zoom no scroll do mouse e pan por arraste — pedido
    do usuário: com muitos vértices próximos os nomes se embolam, então
    precisa dar zoom e mover o desenho pra separar visualmente."""

    def __init__(self, cena: QGraphicsScene) -> None:
        super().__init__(cena)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._zoom = 1.0

    def wheelEvent(self, event: QWheelEvent) -> None:
        fator = _FATOR_ZOOM if event.angleDelta().y() > 0 else 1 / _FATOR_ZOOM
        novo_zoom = self._zoom * fator
        if not (_ZOOM_MINIMO <= novo_zoom <= _ZOOM_MAXIMO):
            return
        self._zoom = novo_zoom
        self.scale(fator, fator)


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

        self.rotulo_area = QLabel()
        self.rotulo_area.setWordWrap(True)
        layout.addWidget(self.rotulo_area)

        self.cena = QGraphicsScene(0, 0, _LARGURA_CENA, _ALTURA_CENA)
        self.view = _VisualizacaoView(self.cena)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view, 1)
        layout.addWidget(QLabel("Role o mouse pra dar zoom; arraste com o botão esquerdo pra mover o desenho."))

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
            self.rotulo_area.setText("")
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
        self._atualizar_area(vertices, tem_cruzamento=bool(cruzamentos))

    def _atualizar_area(self, vertices: list[Vertice], tem_cruzamento: bool) -> None:
        if tem_cruzamento:
            self.rotulo_area.setText("Área (SGL/INCRA) não calculada: o perímetro tem lados que se cruzam.")
            return
        pontos_geodesicos = [(v.n_lat, v.e_long, v.h) for v in vertices]
        try:
            with warnings.catch_warnings(record=True) as avisos_capturados:
                warnings.simplefilter("always")
                resultado = area_sgl(pontos_geodesicos)
        except ValueError as exc:
            self.rotulo_area.setText(f"Área (SGL/INCRA) não calculada: {exc}")
            return
        texto = f"Área (Sistema Geodésico Local, INCRA): {resultado['area_ha']:.4f} ha ({resultado['area_m2']:.2f} m²)"
        if avisos_capturados:
            texto += f"\n⚠ {avisos_capturados[0].message}"
        self.rotulo_area.setText(texto)

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
            fonte = rotulo.font()
            fonte.setPointSize(_TAMANHO_ROTULO_PT)
            rotulo.setFont(fonte)
            # pedido do usuário: o nome do vértice fica sempre no mesmo
            # tamanho na tela, não cresce/encolhe junto com o zoom do
            # desenho — só a POSIÇÃO acompanha o zoom/pan, não o tamanho.
            rotulo.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
            rotulo.setPos(ponto.x() + _RAIO_PONTO + 2, ponto.y() - 10)
            self.cena.addItem(rotulo)

        # espaço extra pra navegar em volta do desenho (pedido do
        # usuário): sem isto, a borda do retângulo envolvente fica
        # apertada bem na ponta do polígono, sem folga pra rolar quando
        # der zoom perto de um vértice na beirada.
        offset_px = _OFFSET_NAVEGACAO_M * escala
        self.cena.setSceneRect(
            self.cena.itemsBoundingRect().adjusted(-offset_px, -offset_px, offset_px, offset_px)
        )
