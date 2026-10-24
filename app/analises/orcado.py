"""Realizado x Orcado: receitas, grupos de custo (soma das contas), contas e Pareto."""
import pandas as pd

from app.analises import base
from app.nucleo.normaliza import regras


def _meses(mes, acumulado):
    return list(range(1, mes + 1)) if acumulado else [mes]


def _resumo(df, sinal):
    """sinal +1 receita (real-orc), -1 custo (orc-real)."""
    orc, ref = df.orcado.sum(), df.orc_ref.sum()
    real = df.realizado.sum(min_count=1)
    dif = None if pd.isna(real) else sinal * (real - ref)
    return {"orcado": orc, "orc_ref": ref, "realizado": real, "dif": dif,
            "dif_pct": (dif / ref) if dif is not None and ref else None,
            "situacao": base.situacao(dif or 0, real, ref)}


def tabela(ano, mes, unidade, acumulado=False) -> dict:
    df = base.linhas(ano, _meses(mes, acumulado), base.filtro_unidades(unidade))
    if df.empty:
        return {"vazio": True}
    rec = df[df.secao == "RECEITA"]
    receitas = [{"grupo": g, **_resumo(x, +1)} for g, x in rec[rec.nivel == 1].groupby("grupo", sort=False)]
    total_rec = _resumo(rec[rec.nivel == 0], +1)

    cus = df[(df.secao == "CUSTO") & (df.nivel == 2)]
    grupos = []
    for gk, x in cus.groupby("grupo_k", sort=False):
        contas = [{"conta": c, "natureza": base.natureza(y.chave.iloc[0]), **_resumo(y, -1)}
                  for c, y in x.groupby("conta", sort=False)]
        contas.sort(key=lambda r: (r["dif"] if r["dif"] is not None else 0))
        grupos.append({"grupo": x.grupo.iloc[0], **_resumo(x, -1), "contas": contas})
    grupos.sort(key=lambda r: (r["dif"] if r["dif"] is not None else 0))
    inv = df[df.secao == "INVESTIMENTO"]
    return {"vazio": False, "receitas": receitas, "receita_total": total_rec,
            "grupos": grupos, "custo_total": _resumo(cus, -1),
            "investimento": _resumo(inv, -1) if not inv.empty else None,
            "status": base.status_periodo(ano, mes, base.filtro_unidades(unidade))}


def pareto(ano, mes, unidade, acumulado=False) -> list:
    """Contas de custo com desvio desfavoravel, ordenadas pelo impacto; marca as que somam 80%."""
    df = base.linhas(ano, _meses(mes, acumulado), base.filtro_unidades(unidade))
    if df.empty:
        return []
    cus = df[(df.secao == "CUSTO") & (df.nivel == 2)]
    g = cus.groupby(["grupo_k", "conta"], sort=False).agg(
        grupo=("grupo", "first"), chave=("chave", "first"), orcado=("orcado", "sum"),
        orc_ref=("orc_ref", "sum"), realizado=("realizado", "sum")).reset_index()
    g["impacto"] = g.realizado - g.orc_ref
    g = g[g.impacto > 0.005].sort_values("impacto", ascending=False)
    total = g.impacto.sum()
    corte = regras()["tolerancias"]["pareto_corte"]
    saida, acum = [], 0.0
    for r in g.itertuples():
        antes = acum
        acum += r.impacto / total
        saida.append({"grupo": r.grupo, "conta": r.conta, "orcado": r.orcado, "orc_ref": r.orc_ref,
                      "realizado": r.realizado, "impacto": r.impacto, "part": r.impacto / total,
                      "acum": acum, "pareto": antes < corte, "natureza": base.natureza(r.chave)})
    return saida


def serie_mensal(ano, unidade) -> list:
    """Receita total e custo operacional por mes (orcado x realizado), para o grafico."""
    df = base.linhas(ano, list(range(1, 13)), base.filtro_unidades(unidade))
    if df.empty:
        return []
    out = []
    for m, x in df.groupby("mes"):
        rec, cus = x[(x.secao == "RECEITA") & (x.nivel == 0)], x[(x.secao == "CUSTO") & (x.nivel == 2)]
        out.append({"mes": int(m), "status": x.status.iloc[0],
                    "rec_orc": rec.orcado.sum(), "rec_real": rec.realizado.sum(),
                    "cus_orc": cus.orcado.sum(), "cus_real": cus.realizado.sum()})
    return out
