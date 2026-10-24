"""Custos por UH / PAX: classificacao total x unidade e decomposicao volume x eficiencia."""
import pandas as pd

from app.analises import base

CLASSES = {
    "A": "Favorável no total e por unidade",
    "B": "Favorável no total, desfavorável por unidade",
    "C": "Desfavorável no total, favorável por unidade",
    "D": "Desfavorável no total e por unidade",
    "E": "Não conclusivo",
}


def _qtd(df):
    """Quantidades por divisor (orcado do mes inteiro e realizado), somadas entre unidades."""
    ind = df[df.secao == "INDICADOR"]
    q = {}
    for cod in ("UH", "PAX", "PAX_TOTAL"):
        x = ind[ind.chave == cod]
        q[cod] = {"orc": x.orcado.sum(), "real": x.realizado.sum(),
                  "orc_ref": (x.orcado * x.pct.where(x.status == "Corrente", 1)).sum()}
    return q


def _classe(dif_total, dif_unit, motivo_e):
    if motivo_e:
        return "E"
    if dif_total >= 0:
        return "A" if dif_unit >= 0 else "B"
    return "C" if dif_unit >= 0 else "D"


def _linha(nome, grupo, x, divisor, q, corrente, nat):
    orc, ref, real = x.orcado.sum(), x.orc_ref.sum(), x.realizado.sum(min_count=1)
    if divisor == "REFEICAO":
        qo = (x.orcado / x.orc_unit).sum() if x.orc_unit.notna().all() else None
        qr = (x.realizado / x.real_unit).sum() if x.real_unit.notna().all() else None
        qref = qo * x.pct.where(x.status == "Corrente", 1).iloc[0] if qo else None
    elif divisor in q:
        qo, qr, qref = q[divisor]["orc"], q[divisor]["real"], q[divisor]["orc_ref"]
    else:
        qo = qr = qref = None
    uo = orc / qo if qo else None
    ur = real / qr if qr and not pd.isna(real) else None
    motivo = None
    if pd.isna(real):
        motivo = "Sem realizado"
    elif not orc:
        motivo = "Sem orçamento"
    elif not divisor or uo is None or ur is None:
        motivo = "Divisor indisponível"
    elif real == 0:
        motivo = "Realizado zerado (possível falta de lançamento)"
    elif corrente and nat in ("C", "D"):
        motivo = "Mês corrente com lançamento não linear"
    dif_t = None if pd.isna(real) else ref - real
    dif_u = (uo - ur) if uo is not None and ur is not None else None
    vol = (qr - qref) * uo if None not in (qr, qref, uo) else None
    efi = (ur - uo) * qr if None not in (ur, uo, qr) else None
    return {"grupo": grupo, "conta": nome, "divisor": divisor, "natureza": nat,
            "orcado": orc, "orc_ref": ref, "realizado": real, "dif_total": dif_t,
            "q_orc": qo, "q_real": qr, "u_orc": uo, "u_real": ur, "dif_unit": dif_u,
            "efeito_volume": vol, "efeito_eficiencia": efi, "motivo": motivo,
            "classe": _classe(dif_t or 0, dif_u or 0, motivo)}


def tabela(ano, mes, unidade) -> dict:
    df = base.linhas(ano, [mes], base.filtro_unidades(unidade))
    if df.empty:
        return {"vazio": True}
    q = _qtd(df)
    corrente = (df.status == "Corrente").any()
    cus = df[(df.secao == "CUSTO") & (df.nivel == 2)]
    contas, grupos = [], []
    for gk, xg in cus.groupby("grupo_k", sort=False):
        for c, x in xg.groupby("conta", sort=False):
            div = x.divisor.dropna().mode()
            k = x.chave.iloc[0]
            contas.append(_linha(c, xg.grupo.iloc[0], x, div.iloc[0] if len(div) else None, q, corrente,
                                 base.natureza(k)))
        grupos.append(_linha(xg.grupo.iloc[0], xg.grupo.iloc[0], xg, "UH", q, corrente, "D" if corrente else "A"))
    total = _linha("Custo operacional total", "", cus, "UH", q, corrente, "D" if corrente else "A")
    total_pax = _linha("Custo operacional total", "", cus, "PAX_TOTAL", q, corrente, "D" if corrente else "A")
    contas.sort(key=lambda r: -abs(r["dif_total"] or 0))
    return {"vazio": False, "contas": contas, "grupos": grupos, "total_uh": total,
            "total_pax": total_pax, "qtd": q, "kpis": kpis(df, q), "classes": CLASSES,
            "status": base.status_periodo(ano, mes, base.filtro_unidades(unidade))}


def kpis(df, q) -> dict:
    """Indicadores operacionais do periodo. Consolidado: medias ponderadas pelos volumes."""
    def soma(secao, k, campo):
        return df[(df.secao == secao) & (df.chave == k)][campo].sum()

    out = {}
    for campo, rot in (("orcado", "orc"), ("realizado", "real")):
        uh, pax = q["UH"][rot], q["PAX"][rot]
        hosp = soma("RECEITA", "VENDAS HOSPEDAGEM", campo)
        ab = soma("RECEITA", "VENDAS A B", campo)
        custo_ab = soma("CUSTO", "CUSTO DE A B", campo)
        ind = df[(df.secao == "INDICADOR")]
        dm = ind[ind.chave == "DIARIA_MEDIA"]
        occ = ind[ind.chave == "OCUPACAO"]
        pesos = ind[ind.chave == "UH"].set_index("unidade")[campo]
        pesos_pax = ind[ind.chave == "PAX"].set_index("unidade")[campo]
        out[rot] = {
            "uh": uh, "pax": pax,
            "diaria_media": _pond(dm, campo, pesos), "ocupacao": _pond(occ, campo, pesos),
            "cmv": custo_ab / ab if ab else None,
            "ab_por_pax": custo_ab / pax if pax else None,
            "couvert": _pond(ind[ind.chave == "COUVERT"], campo, pesos_pax),  # base da planilha
            "receita_hosp": hosp, "receita_ab": ab,
        }
    return out


def _pond(x, campo, pesos):
    x = x.set_index("unidade")[campo].dropna()
    w = pesos.reindex(x.index).fillna(0)
    return float((x * w).sum() / w.sum()) if w.sum() else (float(x.mean()) if len(x) else None)
