"""Ritmo do mes corrente: receita diaria, orcamento proporcional e receita diaria necessaria."""
import calendar
import datetime as dt

import pandas as pd

from app.analises import base


def _serie(d, aba, tipo, conta, dia_max):
    x = d[(d.aba == aba) & (d.tipo == tipo) & (d.conta == conta) & (d.dia >= 1) & (d.dia <= dia_max)]
    return x.groupby("dia").valor.sum()


def tabela(ano, mes, unidade) -> dict:
    unid = base.filtro_unidades(unidade)
    st = base.status_periodo(ano, mes, unid)
    if not st["existe"]:
        return {"vazio": True}
    d = base.diario(ano, mes, unid)
    lin = base.linhas(ano, [mes], unid)
    dia, dias = st["dia_lancado"], st["dias_mes"]

    rec_dia = _serie(d, "VENDAS", "TOTAL", "VENDAS", dia)
    hosp = _serie(d, "VENDAS", "GRUPO", "HOSPEDAGEM", dia)
    ab = _serie(d, "VENDAS", "GRUPO", "A&B", dia)
    uh = _serie(d, "VENDAS", "INDICADOR", "UH", dia)
    pax = _serie(d, "VENDAS", "INDICADOR", "PAX", dia)
    cus = _serie(d, "CUSTOS", "TOTAL", "CUSTOS", dia)
    inv = d[(d.aba == "CUSTOS") & (d.tipo == "INVESTIMENTO") & (d.dia >= 1) & (d.dia <= dia)].groupby("dia").valor.sum()

    rec = lin[lin.secao == "RECEITA"]
    # Orcamento na mesma base da aba VENDAS: total RECEITA + EVENTOS (que a METAS deixa fora do total)
    orc_mes = rec[rec.nivel == 0].orcado.sum() + rec[(rec.nivel == 1) & (rec.chave == "EVENTOS")].orcado.sum()
    acum = float(rec_dia.sum())
    restantes = max(dias - dia, 0)
    media = acum / dia if dia else None
    saldo = orc_mes - acum
    necessaria = saldo / restantes if restantes else None
    ult7 = rec_dia.reindex(range(max(1, dia - 6), dia + 1)).fillna(0)

    tabela_dias = []
    for n in range(1, dias + 1):
        data = dt.date(ano, mes, n)
        lancado = n <= dia
        r, u = rec_dia.get(n), uh.get(n)
        tabela_dias.append({
            "dia": n, "semana": ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"][data.weekday()],
            "fds": data.weekday() >= 4, "lancado": lancado,
            "receita": r if lancado else None, "hospedagem": hosp.get(n) if lancado else None,
            "ab": ab.get(n) if lancado else None, "uh": u if lancado else None,
            "pax": pax.get(n) if lancado else None,
            "rec_uh": (r / u) if lancado and r and u else None,
            "custo": cus.get(n) if lancado else None,
            "investimento": inv.get(n) if lancado else None,
        })
    lan = pd.DataFrame([t for t in tabela_dias if t["lancado"]])
    fds = lan[lan.fds].receita.mean() if not lan.empty else None
    util = lan[~lan.fds].receita.mean() if not lan.empty else None
    return {
        "vazio": False, "status": st, "corrente": st["status"] == "Corrente",
        "orc_mes": orc_mes, "orc_prop": orc_mes * st["pct"], "acumulado": acum,
        "dif_prop": acum - orc_mes * st["pct"], "media_diaria": media, "saldo": saldo,
        "restantes": restantes, "necessaria": necessaria,
        "indice": (media / necessaria) if media and necessaria and necessaria > 0 else None,
        "media_7d": float(ult7.mean()) if len(ult7) else None,
        "indice_7d": (ult7.mean() / necessaria) if necessaria and necessaria > 0 else None,
        "media_fds": fds, "media_util": util,
        "uh_acum": float(uh.sum()), "pax_acum": float(pax.sum()),
        "custo_acum": float(cus.sum()), "dias": tabela_dias,
        "pendentes": pendentes_concentrados(lin) if st["status"] == "Corrente" else [],
        "dias_semana_mes": calendar.monthrange(ano, mes)[1],
    }


def pendentes_concentrados(lin) -> list:
    """Contas de lancamento concentrado (C) ou fixo (B) com orcamento e sem realizado no mes."""
    c = lin[(lin.secao == "CUSTO") & (lin.nivel == 2)]
    g = c.groupby(["grupo", "conta"], sort=False).agg(chave=("chave", "first"), orcado=("orcado", "sum"),
                                                     realizado=("realizado", "sum")).reset_index()
    g["natureza"] = g.chave.map(base.natureza)
    g = g[(g.orcado > 0) & (g.realizado.fillna(0) == 0) & (g.natureza.isin(["B", "C"]))]
    return g.sort_values("orcado", ascending=False).to_dict("records")
