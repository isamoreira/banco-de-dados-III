# Teses e dissertações do PGCOMP/UFBA

Trabalho de Banco de Dados III: coleta, análise e visualização das defesas de mestrado e doutorado do programa, a partir da [página pública de defesas do SIGAA/UFBA](https://sigaa.ufba.br/sigaa/public/programa/defesas.jsf?lc=pt_BR&id=1820) (programa id 1820).

**Site:** https://isamoreira.github.io/banco-de-dados-III/

| Página | O que mostra |
|---|---|
| [Dashboard](https://isamoreira.github.io/banco-de-dados-III/dashboard.html) | Indicadores e gráficos com filtros por ano, tipo e orientador; lista de teses e dissertações com busca, resumo e abstract |
| [Análise geral, 2017–2026](https://isamoreira.github.io/banco-de-dados-III/relatorios/defesas_geral.html) | Defesas por ano e mês, orientadores, bancas, temas e qualidade dos dados |
| [Análise 2025–2026](https://isamoreira.github.io/banco-de-dados-III/relatorios/defesas_2025_2026.html) | O mesmo estudo para os dois últimos anos, com a lista das defesas |
| [Termos dos títulos e resumos](https://isamoreira.github.io/banco-de-dados-III/relatorios/termos.html) | Termos mais usados, em alta e em baixa, e característicos de cada ano, tipo e orientador (TF-IDF) |
| [Relatório parcial PGCOMP](https://isamoreira.github.io/banco-de-dados-III/relatorios/parcial_pgcomp.html) | Contexto do programa, CAPES, linhas de pesquisa, orientadores e ODS |
| [Relatório parcial 2025–2026](https://isamoreira.github.io/banco-de-dados-III/relatorios/parcial_pgcomp_2025_2026.html) | Universo, classificação, produção e depósito dos trabalhos recentes |

## Estrutura

```
├── index.html                 página inicial do site
├── dashboard.html             dashboard (gerado por scripts/gerar_site.py)
├── defesas_dashboard.json     dados do dashboard (precisa ficar ao lado do dashboard.html)
├── relatorios/                relatórios em HTML
├── dados/                     defesas_1820.csv e defesas_1820.xlsx (resultado do scraping)
├── imagens/                   gráficos em PNG
└── scripts/                   código Python e o código-fonte do dashboard
```

## Como atualizar os dados

Requer Python 3 com `pandas`, `numpy`, `beautifulsoup4` e `openpyxl`:

```bash
pip install pandas numpy beautifulsoup4 openpyxl
```

Rode os comandos a partir da pasta principal do repositório, nesta ordem:

```bash
python scripts/scrape_defesas.py              # baixa as defesas do SIGAA -> dados/
python scripts/analise_defesas.py             # relatório geral -> relatorios/defesas_geral.html
python scripts/analise_defesas.py --anos 2025 2026   # recorte -> relatorios/defesas_2025_2026.html
python scripts/analise_termos.py              # termos (TF-IDF) -> relatorios/termos.html e dados/termos_por_defesa.csv
python scripts/gerar_dados_dashboard.py       # dados do dashboard -> defesas_dashboard.json
python scripts/gerar_site.py                  # dashboard -> dashboard.html
```

Depois faça commit e envie; o GitHub Pages atualiza o site em cerca de um minuto.

## Observações

- Os nomes de orientadores e membros de banca são padronizados sem acento e sem diferença de maiúsculas, porque o SIGAA registra a mesma pessoa com grafias diferentes.
- A classificação de títulos em inglês é automática e aproximada.
- O `dashboard.html` não funciona aberto direto do computador (`file://`), porque o navegador bloqueia a leitura do arquivo de dados. Use o site ou um servidor local: `python -m http.server` e abra `http://localhost:8000/dashboard.html`.
