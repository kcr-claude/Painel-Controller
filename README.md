# Controller de Custos e Performance Hoteleira

Aplicação web do Grupo ARA para acompanhar receitas, custos e indicadores do Samoa Beach e do Samoa Villa a partir das planilhas mensais "CUSTOS & RECEITAS I GERAL".

Responsável: Kleber Ribeiro (Gerência Administrativo-Financeira).

## Telas

| Tela | Conteúdo |
|---|---|
| Painel | Indicadores do período, receita x custo por mês, maiores desvios, alertas |
| Realizado x Orçado | Receitas, grupos e contas; mês ou acumulado; Pareto 80% |
| Ritmo do mês | Receita diária, orçamento proporcional, receita diária necessária, contas fixas ainda não lançadas |
| Custos por UH e PAX | Classes A a E (total x unidade), efeito volume x eficiência |
| Qualidade dos dados | 15 checagens por arquivo (esperado x atual, OK/ALERTA) |
| Importar planilhas | Upload de um ou vários .xlsx; reimportar substitui o mês |

## Executar no Windows

1. Instalar Python 3.12 (python.org), marcando "Add python.exe to PATH".
2. Dar dois cliques em `iniciar.bat`. Na primeira vez prepara o ambiente; depois abre http://localhost:8000.
3. Novas planilhas: tela Importar planilhas, ou arrastar a pasta sobre `carregar_pasta.bat`.

## Executar (linha de comando)

```bash
pip install -r requirements.txt
python -m scripts.carregar_pasta "<pasta das planilhas>"   # carga inicial em lote
uvicorn app.web.app:app --host 0.0.0.0 --port 8000
```

Docker: `docker compose up -d --build` (banco em `./dados`). Login opcional: `CONTROLLER_USUARIOS="kleber:senha,outro:senha"`. PostgreSQL: `CONTROLLER_DB_URL=postgresql+psycopg://...`.

Testes: `pytest` (conferência contra as planilhas: `CONTROLLER_PLANILHAS=<pasta> pytest`).

## Estrutura (um arquivo por responsabilidade)

```
app/config/regras.json        grupos, indicadores, aliases, natureza dos custos, tolerâncias
app/nucleo/normaliza.py       chave de conta, números
app/nucleo/db.py              tabelas (arquivo, metas_linha, metas_bloco, diario, erro_formula)
app/importador/identifica.py  unidade/mês/tipo pelo nome do arquivo
app/importador/parametros.py  aba ANÁLISE (dia lançado) e erros de fórmula
app/importador/metas.py       aba METAS: orçado x realizado por linha, divisor
app/importador/diario.py      abas VENDAS e CUSTOS por dia
app/importador/carga.py       grava no banco
app/analises/base.py          leitura, status Fechado/Corrente, orçamento proporcional
app/analises/orcado.py        Realizado x Orçado e Pareto
app/analises/ritmo.py         ritmo do mês corrente
app/analises/unitarios.py     custos por UH/PAX, classes e volume x eficiência
app/analises/qualidade.py     checagens
app/web/                      rotas, telas (templates) e estilo
```

Conta, grupo ou unidade nova: ajustar `regras.json`, sem mexer no código.

## Regras de cálculo

- Status: o mês mais recente de cada unidade com último dia lançado menor que os dias do mês é Corrente; os demais, Fechado.
- Mês corrente: orçado proporcional = orçado do mês × (dia lançado ÷ dias do mês). Indicativo.
- Diferença favorável: receita = realizado − orçado; custo = orçado − realizado.
- Grupo de custo = soma das contas. O subtotal da planilha é conferido em Qualidade.
- Investimentos ficam fora do custo operacional.
- Divisor de cada conta inferido da METAS (orçado ÷ orçado por unidade comparado a UH, PAX e PAX total); sem inferência no mês, usa o histórico da conta.
- CMV = Custo de A&B ÷ Vendas A&B (mesma base da planilha). Couvert médio e diária média: valores da planilha, ponderados no consolidado.

## Pendências

- Planilhas A&B (por ponto de venda) reconhecidas, ainda não integradas. Até lá não há conciliação CUSTOS x METAS, porque a METAS recebe linhas de outras fontes (ex.: Custo de A&B).
- La Fleur Collection sem planilhas na pasta.
- Natureza dos custos (A/B/C) em `regras.json` é uma proposta inicial para validação.
- "RPA" (2025) tratado como conta com detalhe por setor, igual a "Mão de Obra Extra" (2026), sem renomear.
