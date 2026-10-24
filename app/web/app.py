"""Aplicacao web (FastAPI). Rotas finas: cada tela chama um modulo de analise."""
import base64
import json
import math
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.analises import base, orcado, qualidade, ritmo, unitarios
from app.importador.carga import importar
from app.web import formatos

AQUI = Path(__file__).resolve().parent
app = FastAPI(title="Controller de Custos e Performance Hoteleira", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")
tpl = Jinja2Templates(directory=AQUI / "templates")
formatos.registrar(tpl.env)


def _limpo(v):
    """Converte NaN/numpy para JSON valido (NaN vira null)."""
    if isinstance(v, dict):
        return {k: _limpo(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_limpo(x) for x in v]
    if hasattr(v, "item"):
        v = v.item()
    return None if isinstance(v, float) and math.isnan(v) else v


tpl.env.filters["json"] = lambda v: Markup(json.dumps(_limpo(v)))


# ---------- acesso (opcional): CONTROLLER_USUARIOS="kleber:senha,ana:senha2" ----------
@app.middleware("http")
async def autenticacao(request: Request, call_next):
    usuarios = dict(u.split(":", 1) for u in os.getenv("CONTROLLER_USUARIOS", "").split(",") if ":" in u)
    if not usuarios or request.url.path.startswith("/static"):
        return await call_next(request)
    cab = request.headers.get("authorization", "")
    if cab.startswith("Basic "):
        u, _, s = base64.b64decode(cab[6:]).decode(errors="ignore").partition(":")
        if u in usuarios and secrets.compare_digest(usuarios[u], s):
            return await call_next(request)
    return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="Controller"'})


# ---------- filtros comuns ----------
def filtros(request: Request) -> dict:
    q = request.query_params
    ano_u, mes_u = base.ultimo_periodo()
    f = {"unidade": q.get("unidade", base.CONSOLIDADO),
         "ano": int(q.get("ano", ano_u or 0)), "mes": int(q.get("mes", mes_u or 0)),
         "acumulado": q.get("modo") == "acumulado"}
    f["unidades"] = [base.CONSOLIDADO] + base.unidades()
    f["periodos"] = base.periodos()
    f["anos"] = sorted({a for a, _ in f["periodos"]})
    return f


def render(request, nome, tela, **ctx):
    f = filtros(request)
    return tpl.TemplateResponse(request, nome, {"f": f, "tela": tela, **ctx})


def sem_dados(f):
    return not f["periodos"]


# ---------- telas ----------
@app.get("/", response_class=HTMLResponse)
def painel(request: Request):
    f = filtros(request)
    if sem_dados(f):
        return render(request, "vazio.html", "painel")
    u = f["unidade"]
    alertas = []
    for un in base.filtro_unidades(u):
        alertas += [dict(c, unidade=un) for c in qualidade.checks(un, f["ano"], f["mes"]) if c["status"] == "ALERTA"]
    return render(request, "painel.html", "painel",
                  t=orcado.tabela(f["ano"], f["mes"], u, f["acumulado"]),
                  un=unitarios.tabela(f["ano"], f["mes"], u),
                  serie=orcado.serie_mensal(f["ano"], u),
                  pareto=orcado.pareto(f["ano"], f["mes"], u, f["acumulado"])[:6],
                  alertas=alertas)


@app.get("/orcado", response_class=HTMLResponse)
def tela_orcado(request: Request):
    f = filtros(request)
    if sem_dados(f):
        return render(request, "vazio.html", "orcado")
    return render(request, "orcado.html", "orcado",
                  t=orcado.tabela(f["ano"], f["mes"], f["unidade"], f["acumulado"]),
                  pareto=orcado.pareto(f["ano"], f["mes"], f["unidade"], f["acumulado"]))


@app.get("/ritmo", response_class=HTMLResponse)
def tela_ritmo(request: Request):
    f = filtros(request)
    if sem_dados(f):
        return render(request, "vazio.html", "ritmo")
    return render(request, "ritmo.html", "ritmo", r=ritmo.tabela(f["ano"], f["mes"], f["unidade"]))


@app.get("/unitarios", response_class=HTMLResponse)
def tela_unitarios(request: Request):
    f = filtros(request)
    if sem_dados(f):
        return render(request, "vazio.html", "unitarios")
    return render(request, "unitarios.html", "unitarios", u=unitarios.tabela(f["ano"], f["mes"], f["unidade"]))


@app.get("/qualidade", response_class=HTMLResponse)
def tela_qualidade(request: Request):
    f = filtros(request)
    if sem_dados(f):
        return render(request, "vazio.html", "qualidade")
    blocos = [{"unidade": un, "checks": qualidade.checks(un, f["ano"], f["mes"])}
              for un in base.filtro_unidades(f["unidade"])]
    return render(request, "qualidade.html", "qualidade", blocos=blocos, grade=qualidade.resumo_arquivos())


@app.get("/importar", response_class=HTMLResponse)
def tela_importar(request: Request):
    return render(request, "importar.html", "importar", resultados=None, arquivos=_arquivos())


@app.post("/importar", response_class=HTMLResponse)
async def receber(request: Request, planilhas: list[UploadFile] = File(...)):
    resultados = []
    for p in planilhas:
        try:
            resultados.append(importar(p.filename, await p.read()))
        except Exception as e:
            resultados.append({"nome": p.filename, "situacao": "falha", "motivo": str(e)})
    return render(request, "importar.html", "importar", resultados=resultados, arquivos=_arquivos())


def _arquivos():
    a = base.arquivos()
    return [] if a.empty else a.sort_values(["unidade", "ano", "mes"], ascending=[True, False, False]).to_dict("records")
