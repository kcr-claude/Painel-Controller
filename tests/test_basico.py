"""Testes puros (sem planilhas): formatos, chave e identificacao de arquivo."""
import pytest

from app.importador.identifica import ArquivoNaoReconhecido, identificar
from app.nucleo.normaliza import chave
from app.web.formatos import brl, pct


def test_brl():
    assert brl(1234567.891) == "R$ 1.234.567,89"
    assert brl(-1500) == "(R$ 1.500,00)"
    assert brl(None) == "–"


def test_pct():
    assert pct(0.1234) == "12,3%"
    assert pct(-0.05) == "(5,0%)"


def test_chave():
    assert chave("Mão de Obra Extra - A&B") == chave("Mão de Obra Extra A&B") == "MAO DE OBRA EXTRA A B"
    assert chave("Consumo Inteno Comercial") == "CONSUMO INTERNO COMERCIAL"


def test_identificar():
    r = identificar("OUT_26 I CUSTOS & RECEITAS I GERAL I SAMOA BEACH.xlsx")
    assert r == {"unidade": "Samoa Beach", "ano": 2026, "mes": 10, "tipo": "GERAL"}
    assert identificar("JAN_25 I A&B I CUSTOS & RECEITAS I SAMOA VILLA.xlsx")["tipo"] == "AB"
    with pytest.raises(ArquivoNaoReconhecido):
        identificar("planilha qualquer.xlsx")
