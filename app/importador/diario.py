"""Leitura das abas diarias VENDAS e CUSTOS (uma coluna por dia).
Linha 1 = total do dia; linhas sem recuo = grupo; com recuo = conta."""
from app.nucleo.normaliza import chave, num, regras, rotulo


def _cabecalho(rows):
    for i, row in enumerate(rows[:8]):
        if len(row) > 1 and chave(row[1]) == "ACUMULADO":
            dias = {c: int(v) for c, v in enumerate(row) if c >= 2 and isinstance(v, (int, float)) and 1 <= v <= 31}
            return i, dias
    raise ValueError("Cabecalho com 'ACUMULADO' nao encontrado")


def ler_aba(wb, aba: str) -> list:
    if aba not in wb.sheetnames:
        return []
    d = regras()["diario"]
    rows = [tuple(r) for r in wb[aba].iter_rows(values_only=True)]
    hdr, dias = _cabecalho(rows)
    saida, grupo = [], None

    def emitir(row, tipo, g, conta):
        saida.append({"aba": aba, "tipo": tipo, "grupo": g, "conta": conta, "dia": 0, "valor": num(row[1])})
        for c, dia in dias.items():
            v = num(row[c]) if c < len(row) else None
            if v:
                saida.append({"aba": aba, "tipo": tipo, "grupo": g, "conta": conta, "dia": dia, "valor": v})

    emitir(rows[0], "TOTAL", aba, aba)
    for row in rows[hdr + 1:]:
        bruto = row[0] if row else None
        if not isinstance(bruto, str) or not bruto.strip():
            continue
        k, nome, recuo = chave(bruto), rotulo(bruto), bruto.startswith(" ")
        if aba == "VENDAS" and k in d["indicadores_vendas"]:
            emitir(row, "INDICADOR", "INDICADORES", d["indicadores_vendas"][k])
        elif not recuo:
            grupo = nome
            tipo = "INVESTIMENTO" if aba == "CUSTOS" and k in d["investimento_custos"] else "GRUPO"
            emitir(row, tipo, grupo, nome)
        else:
            emitir(row, "CONTA", grupo, nome)
    return saida
