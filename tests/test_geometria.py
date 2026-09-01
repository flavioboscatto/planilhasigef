"""Testes de core/validators/geometria.py — reordena_norte_horario
(sem teste dedicado até agora) e a nova verificar_autointersecao (V3):
imóvel é polígono fechado, lados não-adjacentes nunca podem se cruzar."""
from __future__ import annotations

from core.models import Vertice
from core.validators.geometria import reordena_norte_horario, verificar_autointersecao


def _v(codigo: str, e_long: float, n_lat: float) -> Vertice:
    return Vertice(codigo=codigo, e_long=e_long, n_lat=n_lat)


def test_reordena_comeca_no_vertice_mais_ao_norte():
    vertices = [_v("SUL", -48.0, -10.0), _v("NORTE", -48.0, -9.0), _v("LESTE", -47.5, -9.5)]

    resultado = reordena_norte_horario(vertices)

    assert resultado[0].codigo == "NORTE"


def test_reordena_inverte_sentido_anti_horario_para_horario():
    # NORTE -> OESTE -> SUL é anti-horário (área com sinal positiva, mesma
    # convenção matemática de x=e_long à direita, y=n_lat pra cima) —
    # espera-se que vire NORTE -> SUL -> OESTE (horário)
    vertices = [_v("NORTE", 0.0, 10.0), _v("OESTE", -5.0, 5.0), _v("SUL", 0.0, 0.0)]

    resultado = reordena_norte_horario(vertices)

    assert [v.codigo for v in resultado] == ["NORTE", "SUL", "OESTE"]


def test_reordena_com_menos_de_3_vertices_nao_mexe():
    vertices = [_v("A", -48.0, -9.0), _v("B", -47.0, -8.0)]

    assert reordena_norte_horario(vertices) == vertices


def test_poligono_simples_nao_gera_cruzamento():
    # triângulo — geometricamente nunca pode se autointersectar
    vertices = [_v("A", -48.0, -9.0), _v("B", -47.5, -9.5), _v("C", -48.0, -10.0)]

    assert verificar_autointersecao(vertices) == []


def test_quadrilatero_borboleta_identifica_o_par_certo():
    # vértices em ordem "cruzada" (A-B-C-D com B e D trocados de posição
    # relativa) forma uma borboleta: lado A-B cruza o lado C-D
    vertices = [
        _v("A", 0.0, 0.0),
        _v("B", 1.0, 1.0),
        _v("C", 1.0, 0.0),
        _v("D", 0.0, 1.0),
    ]

    cruzamentos = verificar_autointersecao(vertices)

    assert len(cruzamentos) == 1
    assert cruzamentos[0].indice_a == 0
    assert cruzamentos[0].indice_b == 2
    assert "A" in cruzamentos[0].mensagem and "B" in cruzamentos[0].mensagem
    assert "C" in cruzamentos[0].mensagem and "D" in cruzamentos[0].mensagem


def test_lados_vizinhos_compartilhando_vertice_nao_e_falso_positivo():
    # quadrilátero simples e válido (quadrado) — lados adjacentes se tocam
    # no vértice comum, isso não pode contar como cruzamento
    vertices = [
        _v("A", 0.0, 0.0),
        _v("B", 1.0, 0.0),
        _v("C", 1.0, 1.0),
        _v("D", 0.0, 1.0),
    ]

    assert verificar_autointersecao(vertices) == []


def test_menos_de_3_vertices_nao_quebra():
    assert verificar_autointersecao([]) == []
    assert verificar_autointersecao([_v("A", 0.0, 0.0)]) == []
    assert verificar_autointersecao([_v("A", 0.0, 0.0), _v("B", 1.0, 1.0)]) == []
