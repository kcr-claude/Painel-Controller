"""Esquema do banco. SQLite por padrao; PostgreSQL via CONTROLLER_DB_URL."""
import os
from functools import lru_cache

from sqlalchemy import (Column, Float, ForeignKey, Integer, MetaData, String, Table,
                        create_engine)

meta = MetaData()

arquivo = Table(
    "arquivo", meta,
    Column("id", Integer, primary_key=True),
    Column("unidade", String(40), index=True),
    Column("ano", Integer), Column("mes", Integer),
    Column("tipo", String(10)),            # GERAL | AB
    Column("nome", String(200)), Column("sha1", String(40)),
    Column("importado_em", String(25)),
    Column("dia_lancado", Integer), Column("dias_mes", Integer),
)

metas_linha = Table(
    "metas_linha", meta,
    Column("arquivo_id", Integer, ForeignKey("arquivo.id", ondelete="CASCADE"), index=True),
    Column("unidade", String(40)), Column("ano", Integer), Column("mes", Integer),
    Column("ordem", Integer), Column("secao", String(12)),   # RECEITA|INDICADOR|CUSTO|INVESTIMENTO
    Column("grupo", String(80)), Column("conta", String(120)), Column("chave", String(120)),
    Column("nivel", Integer),              # 0 total, 1 grupo, 2 conta, 3 detalhe
    Column("orcado", Float), Column("realizado", Float),
    Column("orc_unit", Float), Column("real_unit", Float), Column("divisor", String(12)),
)

metas_bloco = Table(  # meses fechados repetidos em arquivos posteriores (conferencia)
    "metas_bloco", meta,
    Column("arquivo_id", Integer, ForeignKey("arquivo.id", ondelete="CASCADE"), index=True),
    Column("unidade", String(40)), Column("ano", Integer), Column("mes_ref", Integer),
    Column("chave", String(120)), Column("orcado", Float), Column("realizado", Float),
)

diario = Table(
    "diario", meta,
    Column("arquivo_id", Integer, ForeignKey("arquivo.id", ondelete="CASCADE"), index=True),
    Column("unidade", String(40)), Column("ano", Integer), Column("mes", Integer),
    Column("aba", String(10)),             # VENDAS | CUSTOS
    Column("tipo", String(12)),            # TOTAL | GRUPO | CONTA | INDICADOR | INVESTIMENTO
    Column("grupo", String(80)), Column("conta", String(120)),
    Column("dia", Integer),                # 0 = acumulado informado na coluna B
    Column("valor", Float),
)

erro = Table(
    "erro_formula", meta,
    Column("arquivo_id", Integer, ForeignKey("arquivo.id", ondelete="CASCADE"), index=True),
    Column("aba", String(20)), Column("celula", String(12)), Column("valor", String(20)),
)


@lru_cache(maxsize=1)
def motor():
    url = os.getenv("CONTROLLER_DB_URL", "sqlite:///dados/controller.db")
    eng = create_engine(url, future=True)
    meta.create_all(eng)
    return eng
