"""Leitura da aba METAS: orcado e realizado por linha.

Cada mes ocupa um bloco de colunas. O ultimo bloco datado antes de 'JANEIRO A ...'
e o mes do proprio arquivo; os anteriores sao meses fechados repetidos (usados so
para conferencia em metas_bloco)."""
import datetime as dt

from app.nucleo.normaliza import chave, num, regras, rotulo


# ---------- blocos de colunas ----------
def localizar_blocos(rows):
    r1, r2 = rows[0], rows[1]
    fim = next((c for c, v in enumerate(r1) if isinstance(v, str) and "JANEIRO" in v.upper()), len(r1))
    inicios = [c for c, v in enumerate(r1[:fim]) if c >= 2 and
               (isinstance(v, dt.datetime) or (isinstance(v, str) and chave(v) == "MES"))]
    blocos = []
    for i, s in enumerate(inicios):
        e = inicios[i + 1] if i + 1 < len(inicios) else fim
        orc = next((c for c in range(s, e) if "ORCADO" in chave(r2[c])), None)
        real = next((c for c in range(s, e) if "REALIZADO" in chave(r2[c])), None)
        if orc is None or real is None:
            continue
        mes = r1[s].month if isinstance(r1[s], dt.datetime) else None
        blocos.append({"inicio": s, "fim": e, "orc": orc, "real": real, "mes": mes})
    return blocos


def _unit(row, ini, fim):
    for c in range(ini, min(fim, len(row))):
        v = num(row[c])
        if v is not None:
            return v
    return None


# ---------- classificacao das linhas ----------
def classificar(rows):
    """Gera (indice_linha, secao, grupo, conta, chave, nivel) seguindo a ordem da aba."""
    m = regras()["metas"]
    ind = m["indicadores"]
    estado, grupo, moe = None, None, None
    for i, row in enumerate(rows):
        bruto = row[0] if row else None
        if not isinstance(bruto, str) or not bruto.strip() or bruto.strip() == "*":
            continue
        k, nome = chave(bruto), rotulo(bruto)
        if estado is None:
            if k == m["inicio_receita"]:
                estado, grupo = "RECEITA", nome
                yield i, "RECEITA", nome, nome, k, 0
            continue
        if estado == "RECEITA":
            if k == m["inicio_indicadores"]:
                estado = "IND"
            elif k in m["grupos_receita_exatos"] or any(k.startswith(chave(p)) for p in m["grupos_receita_prefixos"]):
                grupo = nome
                yield i, "RECEITA", grupo, nome, k, 1
                continue
            else:
                yield i, "RECEITA", grupo, nome, k, 2
                continue
        if estado == "IND":
            if k in ind:
                yield i, "INDICADOR", "INDICADORES", nome, ind[k], 1
                if k == m["fim_indicadores"]:
                    estado = "MEMO"
                continue
        if estado in ("IND", "MEMO"):
            if k == m["inicio_custos"]:
                estado = "CUSTO"
            continue
        if estado == "CUSTO":
            if moe and (k.startswith(moe + " ") or k in m["setores_moe"]):
                # detalhe por setor (no modelo antigo vem so o nome do setor)
                kk = k if k.startswith(moe) else f"{moe} {k}"
                yield i, "CUSTO", grupo, nome, kk, 3
            elif k in m["investimento"]:
                estado = "POS"
                yield i, "INVESTIMENTO", nome, nome, k, 1
            elif k in m["grupos_custo"]:
                grupo, moe = nome, None
                yield i, "CUSTO", grupo, nome, k, 1
            elif k in ind:
                yield i, "INDICADOR", "INDICADORES", nome, ind[k], 1
            elif k in m["contas_com_setor"]:
                moe = k
                yield i, "CUSTO", grupo, nome, k, 2
            else:
                moe = None
                yield i, "CUSTO", grupo, nome, k, 2
            continue
        if estado == "POS" and k in ind:
            yield i, "INDICADOR", "INDICADORES", nome, ind[k], 1


# ---------- divisor ----------
def inferir_divisor(k, orc, orc_unit, real_unit, qtd):
    """Compara orcado/orcado-por-unidade com UH, PAX e PAX_TOTAL orcados."""
    tol = regras()["tolerancias"]["divisor_rel"]
    if orc and orc_unit:
        razao = orc / orc_unit
        for nome in ("UH", "PAX", "PAX_TOTAL"):
            q = qtd.get(nome)
            if q and abs(razao - q) / q <= tol:
                return nome
    if real_unit and "REFEIT" in k:
        return "REFEICAO"
    return None


# ---------- leitura ----------
def ler_metas(wb, mes_arquivo: int) -> dict:
    rows = [tuple(r) for r in wb["METAS"].iter_rows(values_only=True)]
    blocos = localizar_blocos(rows)
    if not blocos:
        raise ValueError("Aba METAS sem blocos ORCADO/REALIZADO reconhecidos")
    atual, fechados = blocos[-1], blocos[:-1]
    linhas_cls = list(classificar(rows))

    def val(i, c):
        return num(rows[i][c]) if c < len(rows[i]) else None

    linhas = []
    for ordem, (i, secao, grupo, conta, k, nivel) in enumerate(linhas_cls):
        linhas.append({
            "ordem": ordem, "secao": secao, "grupo": grupo, "conta": conta, "chave": k, "nivel": nivel,
            "orcado": val(i, atual["orc"]), "realizado": val(i, atual["real"]),
            "orc_unit": _unit(rows[i], atual["orc"] + 1, atual["real"]),
            "real_unit": _unit(rows[i], atual["real"] + 1, atual["real"] + 2),
        })
    qtd = {l["chave"]: l["orcado"] for l in linhas if l["secao"] == "INDICADOR"}
    for l in linhas:
        if l["secao"] in ("CUSTO", "INVESTIMENTO"):
            l["divisor"] = inferir_divisor(l["chave"], l["orcado"], l["orc_unit"], l["real_unit"], qtd)
        else:
            l["divisor"] = None

    conferencia = []
    for b in fechados:
        if not b["mes"] or b["mes"] >= mes_arquivo:
            continue
        for i, secao, grupo, conta, k, nivel in linhas_cls:
            if nivel <= 2:
                conferencia.append({"mes_ref": b["mes"], "chave": f"{chave(grupo)}|{k}",
                                    "orcado": val(i, b["orc"]), "realizado": val(i, b["real"])})
    return {"linhas": linhas, "blocos": conferencia, "mes_bloco": atual["mes"] or mes_arquivo,
            "colunas": (atual["inicio"], atual["fim"])}
