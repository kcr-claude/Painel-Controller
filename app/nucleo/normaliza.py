"""Funcoes puras de normalizacao: chave de conta, numero e acesso as regras."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

REGRAS = Path(__file__).resolve().parent.parent / "config" / "regras.json"


@lru_cache(maxsize=1)
def regras() -> dict:
    return json.loads(REGRAS.read_text(encoding="utf-8"))


def chave(texto) -> str:
    """'Mão de Obra Extra - A&B' -> 'MAO DE OBRA EXTRA A B'. Aplica aliases."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", " ", t).strip().upper()
    return regras()["aliases"].get(t, t)


def rotulo(texto) -> str:
    """Texto exibido: sem quebras de linha e espacos duplicados."""
    return re.sub(r"\s+", " ", str(texto or "")).strip()


def num(v):
    """Valor numerico ou None (erros de formula e textos viram None)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def erro_formula(v) -> bool:
    return isinstance(v, str) and v.strip().startswith("#") and v.strip().endswith(("!", "?", "A"))
