"""Filtros de exibicao: R$ 1.000.000,00 (negativo entre parenteses), 0,0%, quantidades."""
import math

MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_CURTO = ["", "JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]


def _vazio(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def _br(v, casas):
    s = f"{abs(v):,.{casas}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def brl(v, casas=2):
    if _vazio(v):
        return "–"
    t = f"R$ {_br(v, casas)}"
    return f"({t})" if v < -0.004 else t


def pct(v, casas=1):
    if _vazio(v):
        return "–"
    t = f"{_br(v * 100, casas)}%"
    return f"({t})" if v < -0.0004 else t


def qtd(v, casas=0):
    if _vazio(v):
        return "–"
    t = _br(v, casas)
    return f"({t})" if v < 0 else t


def sinal(v):
    """Classe CSS pelo sinal da diferenca favoravel (positivo = favoravel)."""
    if _vazio(v) or abs(v) < 0.005:
        return "neutro"
    return "fav" if v > 0 else "desf"


def registrar(env):
    env.filters.update(brl=brl, pct=pct, qtd=qtd, sinal=sinal)
    env.globals.update(MESES=MESES, MESES_CURTO=MESES_CURTO)
