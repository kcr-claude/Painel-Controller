"""Acesso aos dados importados (DataFrames) e status do periodo."""
import pandas as pd
from sqlalchemy import text

from app.nucleo import db
from app.nucleo.normaliza import chave, regras

CONSOLIDADO = "Consolidado"


def _sql(q, **p) -> pd.DataFrame:
    with db.motor().connect() as cx:
        return pd.read_sql(text(q), cx, params=p)


def arquivos() -> pd.DataFrame:
    """Arquivos com status: o mes mais recente de cada unidade com dia_lancado < dias_mes e Corrente."""
    a = _sql("select * from arquivo where tipo='GERAL' order by unidade, ano, mes")
    if a.empty:
        return a.assign(status=[], pct=[], periodo=[])
    a["periodo"] = a.ano * 100 + a.mes
    a["pct"] = (a.dia_lancado / a.dias_mes).clip(upper=1).fillna(0)
    ult = a.groupby("unidade").periodo.transform("max")
    a["status"] = "Fechado"
    a.loc[(a.periodo == ult) & (a.dia_lancado < a.dias_mes), "status"] = "Corrente"
    return a


def unidades() -> list:
    return sorted(arquivos().unidade.unique().tolist())


def filtro_unidades(unidade: str) -> list:
    return unidades() if unidade in (None, "", CONSOLIDADO) else [unidade]


def periodos() -> list:
    a = arquivos()
    return sorted({(int(r.ano), int(r.mes)) for r in a.itertuples()})


def ultimo_periodo():
    p = periodos()
    return p[-1] if p else (None, None)


def linhas(ano: int, meses: list, unid: list) -> pd.DataFrame:
    """Linhas de METAS do(s) mes(es), com status, % decorrido e orcado de referencia."""
    a = arquivos()
    a = a[(a.ano == ano) & (a.mes.isin(meses)) & (a.unidade.isin(unid))]
    if a.empty:
        return pd.DataFrame()
    ids = ",".join(str(int(i)) for i in a.id)
    m = _sql(f"select * from metas_linha where arquivo_id in ({ids})")
    m = m.merge(a[["id", "status", "pct", "dia_lancado", "dias_mes"]], left_on="arquivo_id", right_on="id")
    m["grupo_k"] = m.grupo.map(chave)
    m["orcado"] = m.orcado.fillna(0.0)
    # Divisor nao inferido no mes: usa o mais frequente da mesma conta nos demais meses
    m["divisor_origem"] = m.divisor.notna().map({True: "mes", False: "historico"})
    m["divisor"] = m.divisor.fillna(m.chave.map(divisores_historicos()))
    # Mes corrente: orcado proporcional ao periodo decorrido (indicativo)
    m["orc_ref"] = m.orcado.where(m.status != "Corrente", m.orcado * m.pct)
    return m


def divisores_historicos() -> dict:
    d = _sql("""select chave, divisor, count(*) n from metas_linha
                where divisor is not null and secao='CUSTO' group by chave, divisor""")
    return d.sort_values("n").drop_duplicates("chave", keep="last").set_index("chave").divisor.to_dict()


def diario(ano: int, mes: int, unid: list) -> pd.DataFrame:
    a = arquivos()
    a = a[(a.ano == ano) & (a.mes == mes) & (a.unidade.isin(unid))]
    if a.empty:
        return pd.DataFrame()
    ids = ",".join(str(int(i)) for i in a.id)
    d = _sql(f"select * from diario where arquivo_id in ({ids})")
    return d.merge(a[["id", "dia_lancado", "dias_mes"]], left_on="arquivo_id", right_on="id")


def status_periodo(ano: int, mes: int, unid: list) -> dict:
    a = arquivos()
    a = a[(a.ano == ano) & (a.mes == mes) & (a.unidade.isin(unid))]
    if a.empty:
        return {"existe": False}
    corrente = (a.status == "Corrente").any()
    return {"existe": True, "status": "Corrente" if corrente else "Fechado",
            "dia_lancado": int(a.dia_lancado.min()), "dias_mes": int(a.dias_mes.max()),
            "pct": float(a.pct.min()), "unidades": a.unidade.tolist(),
            "faltantes": sorted(set(unid) - set(a.unidade))}


def natureza(chave_conta: str) -> str:
    n = regras()["natureza_custo"]
    for tipo in ("A", "B", "C"):
        if chave_conta in n[tipo]:
            return tipo
    return "D"


def situacao(dif, realizado, orcado):
    if realizado is None or pd.isna(realizado):
        return "Dado pendente"
    if not orcado and not realizado:
        return "Sem movimento"
    if abs(dif) < 0.005:
        return "No orçamento"
    return "Favorável" if dif > 0 else "Desfavorável"
