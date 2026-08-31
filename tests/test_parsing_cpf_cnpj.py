"""Testes da máscara progressiva de CPF/CNPJ (core/parsing.py)."""
from __future__ import annotations

from core.parsing import formatar_cpf_cnpj


def test_formata_progressivamente_como_cpf_ate_11_digitos():
    assert formatar_cpf_cnpj("1") == "1"
    assert formatar_cpf_cnpj("123") == "123"
    assert formatar_cpf_cnpj("1234") == "123.4"
    assert formatar_cpf_cnpj("123456789") == "123.456.789"
    assert formatar_cpf_cnpj("12345678900") == "123.456.789-00"


def test_a_partir_do_12o_digito_vira_cnpj():
    assert formatar_cpf_cnpj("123456789000") == "12.345.678/9000"
    assert formatar_cpf_cnpj("12345678000199") == "12.345.678/0001-99"


def test_ignora_qualquer_pontuacao_ja_existente_colada_de_fora():
    assert formatar_cpf_cnpj("123.456.789-00") == "123.456.789-00"
    assert formatar_cpf_cnpj("12.345.678/0001-99") == "12.345.678/0001-99"
    assert formatar_cpf_cnpj("249.087.108-05") == "249.087.108-05"


def test_trunca_alem_de_14_digitos():
    assert formatar_cpf_cnpj("123456789000199999") == "12.345.678/9000-19"


def test_vazio_fica_vazio():
    assert formatar_cpf_cnpj("") == ""
