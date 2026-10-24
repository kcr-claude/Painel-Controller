"""Confere numeros da plataforma contra celulas lidas diretamente das planilhas.
Roda so se CONTROLLER_PLANILHAS apontar para a pasta das planilhas ja importadas."""
import os
from pathlib import Path

import openpyxl
import pytest

from app.analises import base, orcado, ritmo

PASTA = os.getenv("CONTROLLER_PLANILHAS")
pytestmark = pytest.mark.skipif(not PASTA, reason="CONTROLLER_PLANILHAS nao definido")


def _wb(nome):
    p = next(Path(PASTA).rglob(nome))
    return openpyxl.load_workbook(p, read_only=True, data_only=True)


def _celula(wb, aba, ref):
    return wb[aba][ref].value


def test_receita_e_folha_out26_beach():
    wb = _wb("OUT_26 I CUSTOS & RECEITAS I GERAL I SAMOA BEACH.xlsx")
    lin = base.linhas(2026, [10], ["Samoa Beach"])
    rec = lin[(lin.secao == "RECEITA") & (lin.nivel == 0)].iloc[0]
    folha = lin[lin.chave == "FOLHA DE PAGAMENTO ENCARGOS"].iloc[0]
    # Bloco do mes corrente em METAS: BQ = orcado, BT = realizado (modelo 2026)
    assert rec.orcado == pytest.approx(_celula(wb, "METAS", "BQ4"))
    assert rec.realizado == pytest.approx(_celula(wb, "METAS", "BT4"))
    linha = next(r for r in range(30, 60) if str(_celula(wb, "METAS", f"A{r}")).startswith("Folha"))
    assert folha.orcado == pytest.approx(_celula(wb, "METAS", f"BQ{linha}"))
    assert folha.realizado == pytest.approx(_celula(wb, "METAS", f"BT{linha}"))


def test_ritmo_bate_com_vendas_e_analise():
    wb = _wb("OUT_26 I CUSTOS & RECEITAS I GERAL I SAMOA BEACH.xlsx")
    r = ritmo.tabela(2026, 10, "Samoa Beach")
    assert r["status"]["dia_lancado"] == _celula(wb, "ANÁLISE", "B3")
    assert r["acumulado"] == pytest.approx(_celula(wb, "VENDAS", "B1"))
    hosp = sum(d["hospedagem"] or 0 for d in r["dias"])
    assert hosp == pytest.approx(_celula(wb, "ANÁLISE", "B15"))  # FAT. REALIZADO hospedagem


def test_custo_grupo_e_soma_das_contas_jan26_villa():
    wb = _wb("JAN_26 I CUSTOS & RECEITAS I GERAL I SAMOA VILLA.xlsx")
    t = orcado.tabela(2026, 1, "Samoa Villa")
    pessoal = next(g for g in t["grupos"] if g["grupo"] == "PESSOAL")
    # Modelo antigo: bloco corrente BM (orcado) / BO (realizado); PESSOAL na linha 35
    assert _celula(wb, "METAS", "A35") == "PESSOAL"
    assert pessoal["realizado"] == pytest.approx(_celula(wb, "METAS", "BO35"))
    assert pessoal["orcado"] == pytest.approx(_celula(wb, "METAS", "BM35"))
