"""Identifica unidade, ano, mes e tipo pelo nome do arquivo.
Padrao: 'OUT_26 I CUSTOS & RECEITAS I GERAL I SAMOA BEACH.xlsx'."""
import re

from app.nucleo.normaliza import chave, regras


class ArquivoNaoReconhecido(ValueError):
    pass


def identificar(nome: str) -> dict:
    r = regras()
    base = chave(nome)
    m = re.match(r"^([A-Z]{3}) (\d{2}) ", base)
    if not m or m.group(1) not in r["meses"]:
        raise ArquivoNaoReconhecido(f"Mes/ano nao encontrado no nome: {nome}")
    unidade = next((v for k, v in r["unidades"].items() if chave(k) in base), None)
    if not unidade:
        raise ArquivoNaoReconhecido(f"Unidade nao reconhecida no nome: {nome}")
    tipo = "GERAL" if " GERAL " in f" {base} " else ("AB" if " A B " in f" {base} " else None)
    if not tipo:
        raise ArquivoNaoReconhecido(f"Tipo (GERAL ou A&B) nao encontrado no nome: {nome}")
    return {"unidade": unidade, "ano": 2000 + int(m.group(2)),
            "mes": r["meses"][m.group(1)], "tipo": tipo}
