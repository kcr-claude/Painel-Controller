"""Checagens de integridade por arquivo (unidade x mes). Cada check: esperado x atual -> OK/ALERTA."""
from functools import lru_cache

import pandas as pd

from app.analises import base
from app.nucleo.normaliza import chave, regras
from app.web.formatos import qtd

TOL = regras()["tolerancias"]["soma"]


def _txt(v):
    if isinstance(v, bool):
        return "Sim" if v else "Não"
    if isinstance(v, float) and not v.is_integer():
        return qtd(v, 2)
    return qtd(v) if isinstance(v, (int, float)) else str(v)


def _check(nome, esperado, atual, racional, detalhe=None, tol=0.0):
    ok = (abs(atual - esperado) <= tol) if isinstance(atual, (int, float)) and isinstance(esperado, (int, float)) \
        else atual == esperado
    return {"nome": nome, "esperado": _txt(esperado), "atual": _txt(atual), "status": "OK" if ok else "ALERTA",
            "racional": racional, "detalhe": detalhe or []}


def checks(unidade: str, ano: int, mes: int) -> list:
    a = base.arquivos()
    arq = a[(a.unidade == unidade) & (a.ano == ano) & (a.mes == mes)]
    if arq.empty:
        return []
    arq = arq.iloc[0]
    aid, dia, dias = int(arq.id), int(arq.dia_lancado or 0), int(arq.dias_mes or 0)
    lin = base.linhas(ano, [mes], [unidade])
    d = base.diario(ano, mes, [unidade])
    erros = base._sql("select aba, celula, valor from erro_formula where arquivo_id=:i", i=aid)
    out = []

    # 1 completude do mes
    if arq.status == "Fechado":
        out.append(_check("Mês fechado com todos os dias lançados", dias, dia,
                          "Mês fechado com último dia lançado menor que o total de dias indica base incompleta."))
    else:
        out.append(_check("Mês corrente: último dia lançado informado", True, dia > 0,
                          "Sem o último dia lançado não é possível calcular orçamento proporcional.",
                          [f"Dia {dia} de {dias}"]))

    # 2 erros de formula
    det = [f"{r.aba}!{r.celula} {r.valor}" for r in erros.itertuples()][:40]
    out.append(_check("Células com erro de fórmula (#REF!, #DIV/0!)", 0, len(erros),
                      "Erros de fórmula indicam referência quebrada ou divisão por zero na planilha.", det))

    # 3 subtotais de grupo
    cus = lin[lin.secao == "CUSTO"]
    div = []
    for gk, x in cus.groupby("grupo_k", sort=False):
        sub = x[x.nivel == 1]
        if sub.empty:
            continue
        for campo in ("orcado", "realizado"):
            s, t = x[x.nivel == 2][campo].fillna(0).sum(), sub[campo].fillna(0).sum()
            if abs(s - t) > TOL:
                div.append(f"{sub.conta.iloc[0]} ({campo}): subtotal {qtd(t, 2)} x soma das contas {qtd(s, 2)}")
    out.append(_check("Subtotal de grupo igual à soma das contas (METAS)", 0, len(div),
                      "A plataforma usa a soma das contas; subtotal divergente aponta fórmula que omite contas.", div))

    # 4 receita total x grupos
    rec = lin[lin.secao == "RECEITA"]
    tot = rec[rec.nivel == 0].realizado.fillna(0).sum()
    soma = rec[rec.nivel == 1].realizado.fillna(0).sum()
    ev = rec[(rec.nivel == 1) & (rec.chave == "EVENTOS")].realizado.fillna(0).sum()
    out.append(_check("Receita total igual à soma dos grupos de receita", round(soma, 2), round(tot, 2),
                      "Verifica se o total RECEITA da METAS inclui todos os grupos.",
                      [f"Diferença {qtd(soma - tot, 2)}; Eventos realizado {qtd(ev, 2)}"], tol=TOL))

    # 5-6 acumulado x soma dos dias
    for aba in ("VENDAS", "CUSTOS"):
        x = d[d.aba == aba]
        b = x[x.dia == 0].groupby(["tipo", "grupo", "conta"]).valor.sum()
        s = x[x.dia > 0].groupby(["tipo", "grupo", "conta"]).valor.sum().reindex(b.index).fillna(0)
        dif = (b.fillna(0) - s).abs()
        ruins = [f"{i[2]}: acumulado {qtd(b[i], 2)} x dias {qtd(s[i], 2)}" for i in dif[dif > TOL].index]
        out.append(_check(f"{aba}: acumulado igual à soma dos dias", 0, len(ruins),
                          "O acumulado da coluna B deve ser a soma das colunas diárias.", ruins[:30]))

    # 7 cross-aba receita
    v_tot = d[(d.aba == "VENDAS") & (d.tipo == "TOTAL") & (d.dia == 0)].valor.sum()
    out.append(_check("VENDAS (total) igual à receita realizada da METAS + Eventos", round(tot + ev, 2),
                      round(v_tot, 2), "Conciliação entre a aba diária e o consolidado do mês.", tol=TOL))

    # 8 (CUSTOS x METAS) fica fora: a METAS recebe linhas de outras fontes (ex.: Custo de A&B da planilha A&B)
    # 9 lancamentos apos o ultimo dia
    pos = d[(d.dia > dia) & (d.tipo.isin(["GRUPO", "INDICADOR", "INVESTIMENTO"]))]
    out.append(_check("Lançamentos após o último dia lançado", 0, len(pos),
                      "Valores depois do último dia informado sugerem parâmetro desatualizado.",
                      [f"{r.aba} {r.conta} dia {r.dia}: {qtd(r.valor, 2)}" for r in pos.itertuples()][:30]))

    # 10 negativos
    neg = lin[(lin.secao.isin(["RECEITA", "CUSTO"])) & (lin.nivel >= 1) & (lin.realizado < 0)]
    out.append(_check("Valores realizados negativos", 0, len(neg),
                      "Negativo em receita ou custo costuma ser estorno ou reclassificação.",
                      [f"{r.conta}: {qtd(r.realizado, 2)}" for r in neg.itertuples()]))

    # 11 realizado sem orcamento
    c2 = cus[cus.nivel == 2]
    sem = c2[(c2.orcado == 0) & (c2.realizado.fillna(0).abs() > TOL)]
    out.append(_check("Contas com realizado e sem orçamento", 0, len(sem),
                      "Despesa sem orçamento precisa de justificativa ou revisão orçamentária.",
                      [f"{r.grupo} / {r.conta}: {qtd(r.realizado, 2)}" for r in sem.itertuples()]))

    # 12 recorrentes sem lancamento
    out.append(recorrentes_sem_lancamento(unidade, ano, mes, c2))

    # 13 divergencia com consolidacao posterior
    out.append(divergencia_posterior(unidade, ano, mes, lin))

    # 14 coerencia operacional diaria
    dd = d[(d.dia >= 1) & (d.dia <= dia)]
    uh = dd[(dd.tipo == "INDICADOR") & (dd.conta == "UH")].set_index("dia").valor
    hosp = dd[(dd.tipo == "GRUPO") & (dd.conta == "HOSPEDAGEM")].set_index("dia").valor
    pax = dd[(dd.tipo == "INDICADOR") & (dd.conta == "PAX")].set_index("dia").valor
    inco = [f"Dia {n}: UH {qtd(uh.get(n, 0))}, hospedagem {qtd(hosp.get(n, 0), 2)}, PAX {qtd(pax.get(n, 0))}"
            for n in range(1, dia + 1)
            if (uh.get(n, 0) > 0 and hosp.get(n, 0) == 0) or (pax.get(n, 0) > 0 and uh.get(n, 0) == 0)]
    out.append(_check("Dias com UH sem receita de hospedagem ou PAX sem UH", 0, len(inco),
                      "Indicadores operacionais incoerentes distorcem custos por UH e por PAX.", inco))

    # 15 divisor
    semdiv = c2[(c2.orcado > 0) & (c2.divisor.isna())]
    out.append(_check("Contas orçadas sem divisor identificado", 0, len(semdiv),
                      "Sem divisor a conta não entra na análise por UH/PAX.",
                      [f"{r.grupo} / {r.conta}" for r in semdiv.itertuples()]))

    # 16 orcamento existe
    out.append(_check("Orçamento de receita cadastrado no mês", True, bool(rec[rec.nivel == 0].orcado.sum() > 0),
                      "Sem orçamento não há comparação Realizado x Orçado."))
    return out


def recorrentes_sem_lancamento(unidade, ano, mes, c2):
    ant = []
    for k in range(1, 4):
        a, m = (ano, mes - k) if mes - k >= 1 else (ano - 1, mes - k + 12)
        x = base.linhas(a, [m], [unidade])
        if not x.empty:
            ant.append(x[(x.secao == "CUSTO") & (x.nivel == 2)][["grupo_k", "chave", "realizado"]])
    det = []
    if len(ant) == 3:
        h = pd.concat(ant)
        rec = h[h.realizado.fillna(0) > 0].groupby(["grupo_k", "chave"]).size()
        rec = set(rec[rec == 3].index)
        for r in c2.itertuples():
            if (r.grupo_k, r.chave) in rec and not (r.realizado or 0):
                det.append(f"{r.grupo} / {r.conta} (orçado {qtd(r.orcado, 2)})")
    return _check("Contas recorrentes sem lançamento no mês", 0, len(det),
                  "Conta lançada nos três meses anteriores e zerada agora: provável falta de lançamento.", det)


def divergencia_posterior(unidade, ano, mes, lin):
    b = base._sql("""select b.chave, b.orcado, b.realizado, a.mes as mes_arq from metas_bloco b
                     join arquivo a on a.id=b.arquivo_id
                     where b.unidade=:u and b.ano=:a and b.mes_ref=:m""", u=unidade, a=ano, m=mes)
    if b.empty:
        return _check("Mês igual na consolidação dos meses seguintes", 0, 0,
                      "Compara o arquivo do mês com o bloco do mesmo mês nos arquivos posteriores.",
                      ["Sem arquivo posterior para comparar"])
    b = b[b.mes_arq == b.mes_arq.max()]
    lin = lin[lin.nivel <= 2].assign(k=lin.grupo.map(chave) + "|" + lin.chave)
    m = lin.groupby("k").realizado.sum().to_frame("proprio").join(b.groupby("chave").realizado.sum().rename("posterior"))
    m = m.fillna(0)
    m = m[(m.proprio - m.posterior).abs() > TOL]
    det = [f"{k.split('|')[1].title()}: arquivo do mês {qtd(r.proprio, 2)} x mês {int(b.mes_arq.max())} {qtd(r.posterior, 2)}"
           for k, r in m.iterrows()]
    return _check("Mês igual na consolidação dos meses seguintes", 0, len(det),
                  "Diferença indica reclassificação ou lançamento posterior ao fechamento.", det[:40])


def resumo_arquivos() -> list:
    """Situacao de todos os arquivos (grade da tela Qualidade). Recalcula so quando a base muda."""
    a = base.arquivos()
    return _resumo_cache(f"{len(a)}|{a.importado_em.max() if len(a) else ''}")


@lru_cache(maxsize=4)
def _resumo_cache(_assinatura) -> list:
    a = base.arquivos()
    out = []
    for r in a.itertuples():
        cs = checks(r.unidade, int(r.ano), int(r.mes))
        out.append({"unidade": r.unidade, "ano": int(r.ano), "mes": int(r.mes), "status": r.status,
                    "dia": r.dia_lancado, "dias": r.dias_mes,
                    "ok": sum(c["status"] == "OK" for c in cs), "alerta": sum(c["status"] == "ALERTA" for c in cs)})
    return out
