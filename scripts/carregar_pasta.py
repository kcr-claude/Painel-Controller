"""Carga em lote: python -m scripts.carregar_pasta <pasta>  (le todos os .xlsx recursivamente)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.importador.carga import importar  # noqa: E402


def main(pasta: str):
    arquivos = sorted(Path(pasta).rglob("*.xlsx"))
    ok = ign = falha = 0
    for p in arquivos:
        if p.name.startswith("~$"):
            continue
        try:
            r = importar(p.name, p.read_bytes())
            if r["situacao"] == "importado":
                ok += 1
                print(f"OK   {p.name}  dia {r.get('dia_lancado')}/{r.get('dias_mes')}  erros {r['erros_formula']}")
            else:
                ign += 1
        except Exception as e:  # registra e segue
            falha += 1
            print(f"FALHA {p.name}: {e}")
    print(f"\nImportados {ok} | ignorados (A&B) {ign} | falhas {falha}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dados/planilhas")
