"""Orquestra a importacao de um arquivo: le, valida e grava (substitui o mesmo mes)."""
import datetime as dt
import hashlib
import io

import openpyxl
from sqlalchemy import delete, insert, select

from app.importador.diario import ler_aba
from app.importador.identifica import identificar
from app.importador.metas import ler_metas
from app.importador.parametros import ler_parametros, varrer_erros
from app.nucleo import db


def importar(nome: str, conteudo: bytes) -> dict:
    info = identificar(nome)
    if info["tipo"] != "GERAL":
        return {**info, "nome": nome, "situacao": "ignorado",
                "motivo": "Planilha A&B ainda não integrada (ver Pendências no README)"}
    wb = openpyxl.load_workbook(io.BytesIO(conteudo), read_only=True, data_only=True)
    try:
        par = ler_parametros(wb)
        metas = ler_metas(wb, info["mes"])
        dia = ler_aba(wb, "VENDAS") + ler_aba(wb, "CUSTOS")
        erros = varrer_erros(wb, metas["colunas"])
    finally:
        wb.close()
    chave_mes = {k: info[k] for k in ("unidade", "ano", "mes")}
    reg = {**info, "nome": nome, "sha1": hashlib.sha1(conteudo).hexdigest(),
           "importado_em": dt.datetime.now().isoformat(timespec="seconds"), **par}
    eng = db.motor()
    with eng.begin() as cx:
        antigos = [r[0] for r in cx.execute(select(db.arquivo.c.id).where(
            *(getattr(db.arquivo.c, k) == v for k, v in chave_mes.items()), db.arquivo.c.tipo == "GERAL"))]
        for t in (db.metas_linha, db.metas_bloco, db.diario, db.erro):
            if antigos:
                cx.execute(delete(t).where(t.c.arquivo_id.in_(antigos)))
        if antigos:
            cx.execute(delete(db.arquivo).where(db.arquivo.c.id.in_(antigos)))
        aid = cx.execute(insert(db.arquivo).values(**reg)).inserted_primary_key[0]
        base = {"arquivo_id": aid, **chave_mes}
        cx.execute(insert(db.metas_linha), [{**base, **l} for l in metas["linhas"]])
        if metas["blocos"]:
            cx.execute(insert(db.metas_bloco), [{"arquivo_id": aid, "unidade": info["unidade"],
                                                 "ano": info["ano"], **b} for b in metas["blocos"]])
        if dia:
            cx.execute(insert(db.diario), [{**base, **d} for d in dia])
        if erros:
            cx.execute(insert(db.erro), [{"arquivo_id": aid, **e} for e in erros])
    return {**info, "nome": nome, "situacao": "importado", "linhas": len(metas["linhas"]),
            "lancamentos_diarios": len(dia), "erros_formula": len(erros), **par}
