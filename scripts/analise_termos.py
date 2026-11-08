"""Análise de termos dos títulos e resumos das defesas com TF-IDF.

Uso (a partir da pasta principal): python scripts/analise_termos.py [--csv dados/defesas_1820.csv]
Gera:
  relatorios/termos.html          relatório com os termos mais usados, característicos e em alta
  dados/termos_por_defesa.csv     os 8 termos mais característicos de cada defesa

Como funciona
  - Cada defesa vira um texto: título (contado 2 vezes, por resumir o trabalho) + resumo em português.
  - Termos são palavras soltas e expressões de 2 ou 3 palavras ("sistemas de recomendação"),
    sem artigos, preposições e palavras genéricas de texto acadêmico ("trabalho", "resultados").
  - TF-IDF dá peso alto a um termo que aparece muito num trabalho e em poucos outros:
      tf  = vezes que o termo aparece no texto / total de termos do texto
      idf = ln((1 + N) / (1 + nº de textos com o termo)) + 1
      peso = tf × idf (cada texto normalizado para ter tamanho 1)
  - Termos característicos de um grupo (ano, orientador, tipo) = maior peso médio entre as
    defesas do grupo, contando só termos presentes em pelo menos 2 delas.
Depende de pandas e numpy.
"""
import argparse
import html
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
# funciona no repositório (scripts/ + dados/) e numa pasta com tudo junto
RAIZ = AQUI.parent if (AQUI.parent / "dados").is_dir() else AQUI
PASTA_DADOS = RAIZ / "dados" if (RAIZ / "dados").is_dir() else RAIZ
PASTA_REL = RAIZ / "relatorios" if (RAIZ / "relatorios").is_dir() else RAIZ

ap = argparse.ArgumentParser(description="Termos dos títulos e resumos (TF-IDF)")
ap.add_argument("--csv", default=str(PASTA_DADOS / "defesas_1820.csv"))
ARGS = ap.parse_args()
SAIDA_HTML = PASTA_REL / "termos.html"
SAIDA_CSV = PASTA_DADOS / "termos_por_defesa.csv"

# ---------------------------------------------------------------- palavras ignoradas
STOP = set("""
a à às ao aos o os as um uma uns umas de da do das dos em no na nos nas num numa por pelo pela pelos pelas
para pra com sem sob sobre entre até após ante contra desde perante e ou mas nem que se como quando onde
qual quais quanto cujo cuja cujos cujas porque pois porém contudo entanto todavia assim também ainda já
mais menos muito muitos muita muitas pouco poucos pouca poucas tão tanto tanta tantos tantas todo toda
todos todas cada outro outra outros outras mesmo mesma mesmos mesmas próprio própria próprios próprias
este esta estes estas esse essa esses essas aquele aquela aqueles aquelas isto isso aquilo ele ela eles
elas seu sua seus suas nosso nossa nossos nossas lhe lhes nós eu meu minha é são ser foi foram será serão
sendo sido era eram está estão estar esteve estava há haver houve tem têm ter tinha tendo pode podem
poder podendo deve devem dever possa possam faz fazem fazer feito feita feitos feitas sim não nao só
apenas bem ser lo la los las vez vezes forma formas modo maneira tipo tipos parte partes meio através
via dentre além aqui ali neste nesta nestes nestas nesse nessa desse dessa deste desta destes destas
disso disto dele dela deles delas cerca sobretudo exemplo ex etc i ii iii iv v vi
""".split())
# palavras típicas de qualquer texto acadêmico, que não dizem o tema
STOP_ACAD = set("""
trabalho trabalhos pesquisa pesquisas estudo estudos dissertação tese proposta propostas propor propõe
propomos proposto proposta propostos apresenta apresentam apresentar apresentado apresentada apresentamos
resultado resultados objetivo objetivos objetiva análise análises abordagem abordagens método métodos
metodologia avaliação avaliar avaliado avaliada avaliados realizado realizada realizados realizadas
realizar utilizado utilizada utilizados utilizadas utilizar utilizando utiliza uso usar usado usada
usados usando base baseado baseada baseados baseadas partir novo nova novos novas diferentes diferente
principais principal importante importantes possível possíveis necessário necessária capaz significativa
significativamente relação contexto área áreas processo processos problema problemas solução soluções
caso casos ponto pontos aspecto aspectos fim estudo final finais além disso dessa desse forma
literatura revisão sistemática mapeamento estado arte autores visa visando busca buscar desenvolvimento
desenvolver desenvolvido desenvolvida demonstra demonstram demonstrar mostram mostra mostrar mostrou
indicam indica permite permitem permitir obtidos obtidas obter obtido existentes existente relacionados
relacionadas investigar investiga investigação analisar analisa analisado identificar identifica
identificado identificados conjunto melhor melhores maior maiores menor menores alto alta altos altas
grande grandes número quantidade aplicação aplicações aplicado aplicada experimento experimentos
experimental experimentais primeiro primeira segundo segunda terceiro dois duas três ano anos atual atuais
cenário cenários estratégia estratégias técnica técnicas ferramenta ferramentas modelo modelos sistema
sistemas dados informação informações tais devido maioria apesar considerando considerar considera diversos
diversas vários várias utilização eficiente eficientes eficiência necessidade necessidades incluindo inclui
eficácia contribui contribuir contribuição contribuições frequentemente múltiplos múltiplas potencial
potenciais avanço avanços medida medidas etapa etapas resolver auxiliar resposta respostas comum comuns
algum alguma alguns algumas portanto apoiar apoio suporte desafio desafios característica características
ambiente ambientes tempo últimos último última últimas longo presente coletados coletadas possui possuem
geral gerais específico específica específicos específicas respectivamente principalmente especialmente
geralmente forma atualmente recentes recente quanto tanto lado sentido termos acordo presença dado dada
dadas dados mundo vista visto tarefa nível níveis aumento aumentar redução reduzir tornar torna tornam
desta deste textit cite emph ieee seja sejam durante embora melhorar melhoria melhorias campo serem
consiste existência rápida rápido importância produzidos produzidas vem vêm capacidade sendo pode
lidar oferece oferecem oferecer crescente extrair ajudar encontrar disponíveis disponível identificação
""".split())
GERUNDIO = re.compile(r".{3,}(ando|endo|indo)$")  # "oferecendo", "mantendo": verbos soltos não dizem o tema
# resumos que vieram em inglês no campo do resumo
STOP_EN = set("""
the of and in for to on an with from by at as is are was were be been being this that these those it its
which who whom whose what when where how why than then there their they them we our us you your he she his
her not no or but if so such can could may might will would shall should must do does did done have has had
having also into over under between through during before after about above below up down out more most
other some any each all both few many much very only own same just new based using use used uses approach
approaches study studies paper work results result propose proposed proposes present presents presented
analysis method methods however therefore thus while well first second three two one data system systems
model models research problem problems solution solutions different several various main
""".split())
STOP |= STOP_EN
# conectivos que podem ficar no meio de uma expressão ("sistemas de recomendação")
MEIO = {"de", "da", "do", "das", "dos", "e", "em", "para", "a", "o"}
# termos genéricos sozinhos, mas úteis dentro de expressões
SO_EM_EXPRESSAO = {"sistema", "sistemas", "dados", "modelo", "modelos", "informação", "informações",
                   "técnica", "técnicas", "ferramenta", "ferramentas", "aplicação", "aplicações",
                   "software", "rede", "redes", "aprendizado", "processo", "processos", "tempo", "dado"}


def tokens(texto):
    return re.findall(r"[a-zà-öø-ÿ0-9]+(?:-[a-zà-öø-ÿ0-9]+)*", texto.lower())


def termos(texto):
    """Palavras e expressões de 2-3 palavras, sem começar nem terminar em palavra ignorada."""
    tk = tokens(texto)
    out = []
    ign = lambda w: w in STOP or w in STOP_ACAD or len(w) < 3 or w.isdigit()
    for i, w in enumerate(tk):
        if not ign(w) and w not in SO_EM_EXPRESSAO and not GERUNDIO.match(w):
            out.append(w)
        for n in (2, 3):
            g = tk[i:i + n]
            if len(g) < n:
                break
            primeira, ultima, meio = g[0], g[-1], g[1:-1]
            if (primeira in STOP or primeira in STOP_ACAD and primeira not in SO_EM_EXPRESSAO or len(primeira) < 3
                    or ultima in STOP or (ultima in STOP_ACAD and ultima not in SO_EM_EXPRESSAO)
                    or len(ultima) < 3 or primeira.isdigit()):
                continue
            if any(m in STOP and m not in MEIO for m in meio):
                continue
            if n == 3 and g[1] not in MEIO:  # 3 palavras só no formato "x de y"
                continue
            if n == 2 and g[1] in MEIO:
                continue
            out.append(" ".join(g))
    return out


def sem_acento(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


# ---------------------------------------------------------------- dados e TF-IDF
d = pd.read_csv(ARGS.csv, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
d["Ano"] = d["Ano"].astype(int)
d["Tipo1"] = d["Tipo"].map({"Dissertações": "Dissertação", "Teses": "Tese"})
d["Orient_key"] = d["Orientador"].map(lambda n: re.sub(r"\s+", " ", sem_acento(n)).strip().upper())
d["texto"] = d["Título"] + ". " + d["Título"] + ". " + d["Resumo"]
docs = [termos(t) for t in d["texto"]]
N = len(docs)

df_cont = Counter(t for doc in docs for t in set(doc))
# vocabulário: palavras em >= 3 defesas, expressões em >= 3; ignora termos em mais de 40% das defesas
vocab = sorted(t for t, c in df_cont.items() if 3 <= c <= 0.4 * N)
idx = {t: i for i, t in enumerate(vocab)}
X = np.zeros((N, len(vocab)))
for i, doc in enumerate(docs):
    c = Counter(t for t in doc if t in idx)
    tot = sum(c.values()) or 1
    for t, n in c.items():
        X[i, idx[t]] = n / tot
dfv = np.array([df_cont[t] for t in vocab])
idf = np.log((1 + N) / (1 + dfv)) + 1
X = X * idf
X = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12)
presente = X > 0

# expressões contidas em outra mais longa com a mesma presença viram redundantes nas listas
def sem_redundancia(lista, k):
    escolhidos = []
    for t in lista:
        if any((t in e or e in t) and t != e for e in escolhidos):
            continue
        escolhidos.append(t)
        if len(escolhidos) == k:
            break
    return escolhidos


def caracteristicos(mask, k=10, min_docs=2):
    sub = X[mask]
    if not len(sub):
        return []
    media = sub.mean(axis=0)
    cont = presente[mask].sum(axis=0)
    ordem = [vocab[j] for j in np.argsort(-media) if cont[j] >= min_docs and media[j] > 0]
    return [(t, int(cont[idx[t]])) for t in sem_redundancia(ordem, k)]


# 1. mais usados (nº de defesas)
expr = sorted((t for t in vocab if " " in t), key=lambda t: -df_cont[t])
palav = sorted((t for t in vocab if " " not in t), key=lambda t: -df_cont[t])
top_expr = [(t, df_cont[t]) for t in sem_redundancia(expr, 25)]
top_palav = [(t, df_cont[t]) for t in palav[:25]]

# 2. por ano (anos com >= 5 defesas)
anos = sorted(a for a, n in d["Ano"].value_counts().items() if n >= 5)
por_ano = {a: caracteristicos((d["Ano"] == a).values, k=8) for a in anos}

# 3. em alta e em baixa: % de defesas que usam o termo, 2018-2021 x 2022-2026
p1 = (d["Ano"] <= 2021).values
p2 = (d["Ano"] >= 2022).values
n1, n2 = p1.sum(), p2.sum()
tend = []
for t in vocab:
    j = idx[t]
    a, b = presente[p1, j].sum(), presente[p2, j].sum()
    if a + b >= 6:
        tend.append((t, a / n1 * 100, b / n2 * 100, int(a), int(b)))
alta = sorted(tend, key=lambda x: -(x[2] - x[1]))
baixa = sorted(tend, key=lambda x: (x[2] - x[1]))
alta = [x for x in alta if x[0] in sem_redundancia([y[0] for y in alta], 15)][:15]
baixa = [x for x in baixa if x[0] in sem_redundancia([y[0] for y in baixa], 15)][:15]

# 4. por tipo
por_tipo = {t: caracteristicos((d["Tipo1"] == t).values, k=12, min_docs=3) for t in ["Dissertação", "Tese"]}

# 5. por orientador (>= 5 defesas)
nome_or = d.groupby("Orient_key")["Orientador"].agg(lambda s: s.mode()[0])
cont_or = d["Orient_key"].value_counts()
por_or = []
for k, n in cont_or.items():
    if n >= 5:
        por_or.append((nome_or[k], int(n), caracteristicos((d["Orient_key"] == k).values, k=6)))

# 6. termos de cada defesa
linhas = []
for i in range(N):
    ordem = [vocab[j] for j in np.argsort(-X[i]) if X[i, j] > 0]
    linhas.append({
        "Ano": d.loc[i, "Ano"], "Tipo": d.loc[i, "Tipo1"], "Nº": d.loc[i, "Nº"],
        "Discente": d.loc[i, "Discente"], "Título": d.loc[i, "Título"],
        "Termos (TF-IDF)": "; ".join(sem_redundancia(ordem, 8)),
    })
pd.DataFrame(linhas).to_csv(SAIDA_CSV, sep=";", index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------- relatório
def esc(x):
    return html.escape(str(x))


def barras(itens, largura=720, sufixo="", cor="s1"):
    """Barras horizontais em SVG: itens = [(rótulo, valor)]."""
    if not itens:
        return '<p class="nota">Sem termos suficientes.</p>'
    lin, ml, mr = 24, 230, 46
    altura = lin * len(itens) + 6
    w = largura - ml - mr
    vmax = max(v for _, v in itens) or 1
    out = [f'<svg viewBox="0 0 {largura} {altura}" class="chart" role="img">']
    for i, (r, v) in enumerate(itens):
        y = 3 + i * lin
        bw = max(2, v / vmax * w)
        out.append(f'<text x="{ml - 8}" y="{y + 15}" class="lbl" text-anchor="end">{esc(r)}</text>')
        out.append(f'<rect x="{ml}" y="{y + 4}" width="{bw:.1f}" height="14" rx="3" class="{cor}">'
                   f"<title>{esc(r)}: {v}{sufixo}</title></rect>")
        out.append(f'<text x="{ml + bw + 6:.1f}" y="{y + 15}" class="val">{v}{sufixo}</text>')
    out.append("</svg>")
    return "".join(out)


def chips(lista):
    return "".join(f'<span class="chip">{esc(t)}<small>{n}</small></span>' for t, n in lista) or "—"


tab_ano = "".join(f"<tr><th>{a}</th><td>{chips(v)}</td></tr>" for a, v in por_ano.items())
tab_or = "".join(f"<tr><th>{esc(n)}<small>{c} defesas</small></th><td>{chips(v)}</td></tr>"
                 for n, c, v in sorted(por_or, key=lambda x: -x[1]))


def tab_tend(lst):
    return "".join(
        f"<tr><td>{esc(t)}</td><td class='n'>{a:.0f}%</td><td class='n'>{b:.0f}%</td>"
        f"<td class='n {'up' if b >= a else 'down'}'>{'+' if b >= a else ''}{b - a:.0f} p.p.</td></tr>"
        for t, a, b, _, _ in lst)


exemplos = pd.DataFrame(linhas).sample(6, random_state=7)
tab_ex = "".join(f"<tr><td>{esc(r['Título'])}<small>{esc(r['Tipo'])} · {r['Ano']}</small></td>"
                 f"<td>{esc(r['Termos (TF-IDF)'])}</td></tr>" for _, r in exemplos.iterrows())

n_expr = sum(" " in t for t in vocab)

# ---- exemplo real do cálculo, para a seção explicativa
alvo = "sistemas de recomendação" if "sistemas de recomendação" in idx else vocab[int(np.argmax(X.max(axis=0)))]
i_ex = int(np.argmax(X[:, idx[alvo]]))
cont_ex = Counter(t for t in docs[i_ex] if t in idx)
tot_ex = sum(cont_ex.values())
presentes_ex = list(cont_ex)
comum = max(presentes_ex, key=lambda t: df_cont[t])          # o termo mais comum no programa
raro = max(presentes_ex, key=lambda t: X[i_ex, idx[t]])      # o de maior peso nesta defesa
norma_ex = float(np.linalg.norm(np.array([cont_ex[t] / tot_ex * idf[idx[t]] for t in presentes_ex])))
linhas_ex = []
for t in dict.fromkeys([raro, alvo, comum]):
    j = idx[t]
    tf = cont_ex[t] / tot_ex
    linhas_ex.append((t, cont_ex[t], tf, df_cont[t], idf[j], tf * idf[j], X[i_ex, j]))
tit_ex = d.loc[i_ex, "Título"]
pos_ex = int((X[i_ex] > 0).sum())


def f2(x, casas=3):
    return f"{x:.{casas}f}".replace(".", ",")


tab_calc = "".join(
    f"<tr><td><b>{esc(t)}</b></td><td class='n'>{n}</td><td class='n'>{n}/{tot_ex} = {f2(tf)}</td>"
    f"<td class='n'>{dfc}</td><td class='n'>{f2(iv, 2)}</td><td class='n'>{f2(w)}</td><td class='n'><b>{f2(wn)}</b></td></tr>"
    for t, n, tf, dfc, iv, w, wn in linhas_ex)
(t_r, n_r, tf_r, df_r, idf_r, w_r, wn_r) = linhas_ex[0]
(t_c, n_c, tf_c, df_c, idf_c, w_c, wn_c) = linhas_ex[-1]
idf_max = np.log((1 + N) / (1 + 3)) + 1
idf_min = np.log((1 + N) / (1 + 0.4 * N)) + 1
corpo = f"""
<header>
  <p class="eyebrow">Análise de termos · TF-IDF</p>
  <h1>Do que falam as teses e dissertações</h1>
  <p class="sub">{N} defesas ({d['Ano'].min()}–{d['Ano'].max()}) · título e resumo em português · vocabulário de
  {len(vocab):,} termos ({n_expr:,} expressões de 2–3 palavras) presentes em pelo menos 3 defesas · gerado em {date.today():%d/%m/%Y}</p>
</header>

<section>
<h2>O que é TF-IDF</h2>
<p>Contar palavras sozinho engana: as palavras que mais aparecem num resumo costumam ser as que aparecem em
quase todos (<i>sistema</i>, <i>dados</i>, <i>desempenho</i>), e por isso não dizem do que aquele trabalho
trata. O <b>TF-IDF</b> (<i>term frequency – inverse document frequency</i>, frequência do termo × inverso da
frequência nos documentos) corrige isso multiplicando duas medidas:</p>
<div class="formula">
  <p><b>TF</b>: quanto o termo aparece <i>neste</i> trabalho<br>
  <code>tf = vezes que o termo aparece no texto ÷ total de termos do texto</code></p>
  <p><b>IDF</b>: quão raro o termo é <i>no conjunto</i> das {N} defesas<br>
  <code>idf = ln( (1 + {N}) ÷ (1 + nº de defesas que usam o termo) ) + 1</code></p>
  <p><b>Peso</b> = <code>tf × idf</code></p>
</div>
<p>Um termo ganha peso alto quando aparece bastante num trabalho <b>e</b> em poucos outros. Neste conjunto o
idf vai de {f2(idf_max, 2)}, para um termo usado em só 3 defesas, até {f2(idf_min, 2)}, para um termo usado em
40% delas. Ou seja, um termo raro vale cerca de {idf_max / idf_min:.0f} vezes mais que um termo muito comum
que apareça o mesmo número de vezes.</p>

<h3>Exemplo com uma defesa real</h3>
<p class="nota">“{esc(tit_ex)}” ({esc(d.loc[i_ex, 'Tipo1'])}, {d.loc[i_ex, 'Ano']}). O texto dessa defesa tem
{tot_ex} ocorrências de termos do vocabulário, de {pos_ex} termos diferentes.</p>
<div class="tab-wrap"><table class="tab">
  <thead><tr><th>Termo</th><th class="n">Vezes no texto</th><th class="n">tf</th><th class="n">Defesas que usam</th>
  <th class="n">idf</th><th class="n">tf × idf</th><th class="n">Peso final</th></tr></thead>
  <tbody>{tab_calc}</tbody>
</table></div>
<p><i>{esc(t_c)}</i> é usado em {df_c} defesas, por isso tem idf baixo ({f2(idf_c, 2)}) e fica com peso
{f2(wn_c)}. <i>{esc(t_r)}</i> aparece em só {df_r}, tem idf {f2(idf_r, 2)} e chega a {f2(wn_r)}: fica entre os
termos que mais descrevem o trabalho. O <b>peso final</b> divide cada tf × idf pelo “tamanho” do conjunto de pesos da defesa
(a raiz da soma dos quadrados, aqui {f2(norma_ex)}). Assim um resumo longo não ganha mais peso que um curto,
e os pesos de defesas diferentes podem ser comparados.</p>
</section>

<section>
<h2>Como o script funciona</h2>
<p>O código está em <code>scripts/analise_termos.py</code> e roda com
<code>python scripts/analise_termos.py</code>. Ele faz, em ordem:</p>
<ol class="passos">
  <li><b>Lê os dados</b> de <code>dados/defesas_1820.csv</code>, gerado pelo scraping do SIGAA: {N} defesas.</li>
  <li><b>Monta um texto por defesa</b>: título + título + resumo em português. O título entra duas vezes
      porque resume o trabalho em poucas palavras.</li>
  <li><b>Quebra o texto em palavras</b>, tudo em minúsculas, mantendo acentos e palavras com hífen
      (<i>edge-cloud</i>).</li>
  <li><b>Gera os termos</b>: palavras soltas e expressões de 2 palavras (<i>dívida técnica</i>) ou de 3 no formato
      “x de y” (<i>internet das coisas</i>). Uma expressão não pode começar nem terminar em palavra ignorada.</li>
  <li><b>Descarta palavras sem tema</b>: artigos, preposições e verbos auxiliares em português e inglês,
      palavras de texto acadêmico (<i>trabalho</i>, <i>proposta</i>, <i>resultados</i>) e verbos no gerúndio.
      Palavras genéricas como <i>sistema</i>, <i>dados</i> e <i>modelo</i> só contam dentro de expressões
      (<i>conjuntos de dados</i>).</li>
  <li><b>Monta o vocabulário</b>: só termos usados em pelo menos 3 defesas (para evitar acasos) e em no máximo
      40% delas (comuns demais para distinguir trabalhos). Sobram {len(vocab):,} termos.</li>
  <li><b>Calcula a matriz TF-IDF</b>: uma tabela de {N} linhas (defesas) × {len(vocab):,} colunas (termos), com o
      peso final de cada termo em cada defesa.</li>
  <li><b>Resume a matriz</b> nas seções abaixo:
    <ul>
      <li><b>mais usados</b>: número de defesas que usam o termo (sem TF-IDF, é uma contagem direta);</li>
      <li><b>em alta e em baixa</b>: percentual de defesas que usam o termo em cada período;</li>
      <li><b>característicos de um grupo</b> (ano, tipo, orientador): média dos pesos TF-IDF nas defesas do grupo,
          contando só termos presentes em pelo menos 2 delas, para um único trabalho não dominar o grupo;</li>
      <li><b>termos de cada defesa</b>: os 8 de maior peso, gravados em <code>dados/termos_por_defesa.csv</code>.</li>
    </ul>
  </li>
</ol>
<p class="nota">Expressões que repetem outra da mesma lista (<i>recomendação</i> dentro de <i>sistemas de
recomendação</i>) são mostradas uma vez só. O número ao lado de cada termo nas listas é a quantidade de defesas
que o usam.</p>
</section>

<section>
<h2>1. Expressões mais usadas</h2>
<p class="nota">Número de defesas que usam a expressão no título ou no resumo.</p>
{barras(top_expr)}
</section>

<section>
<h2>2. Palavras mais usadas</h2>
<p class="nota">Palavras soltas, sem as genéricas (<i>sistema</i>, <i>dados</i>, <i>modelo</i> ficam só dentro de expressões).</p>
{barras(top_palav)}
</section>

<section>
<h2>3. Termos em alta e em baixa</h2>
<p class="nota">Percentual de defesas que usam o termo em 2018–2021 ({n1} defesas) e em 2022–2026 ({n2} defesas),
para termos presentes em pelo menos 6 defesas. p.p. = pontos percentuais.</p>
<div class="duas">
  <div><h3>Em alta</h3><table class="tab"><thead><tr><th>Termo</th><th class="n">2018–21</th><th class="n">2022–26</th><th class="n">Variação</th></tr></thead><tbody>{tab_tend(alta)}</tbody></table></div>
  <div><h3>Em baixa</h3><table class="tab"><thead><tr><th>Termo</th><th class="n">2018–21</th><th class="n">2022–26</th><th class="n">Variação</th></tr></thead><tbody>{tab_tend(baixa)}</tbody></table></div>
</div>
</section>

<section>
<h2>4. Termos característicos de cada ano</h2>
<p class="nota">Maior peso TF-IDF médio entre as defesas do ano (termo presente em pelo menos 2 delas). Anos com menos de 5 defesas ficam de fora.</p>
<table class="tab grupos"><tbody>{tab_ano}</tbody></table>
</section>

<section>
<h2>5. Dissertações x teses</h2>
<p class="nota">Termos de maior peso médio em cada tipo (presentes em pelo menos 3 defesas do tipo).</p>
<div class="duas">
  <div><h3>Dissertações</h3>{chips(por_tipo['Dissertação'])}</div>
  <div><h3>Teses</h3>{chips(por_tipo['Tese'])}</div>
</div>
</section>

<section>
<h2>6. Termos característicos por orientador</h2>
<p class="nota">Orientadores com 5 ou mais defesas. Mostra os temas que cada um mais orienta.</p>
<table class="tab grupos"><tbody>{tab_or}</tbody></table>
</section>

<section>
<h2>7. Termos de cada defesa (exemplos)</h2>
<p class="nota">Os 8 termos de maior peso de cada defesa estão em <code>{esc(SAIDA_CSV.name)}</code>. Alguns exemplos:</p>
<table class="tab"><thead><tr><th>Defesa</th><th>Termos mais característicos</th></tr></thead><tbody>{tab_ex}</tbody></table>
</section>

<section>
<h2>Limites</h2>
<ul>
  <li>Contagem de palavras não entende sentido: sinônimos (<i>aprendizado de máquina</i> e <i>machine learning</i>) contam separado.</li>
  <li>Resumos com termos em inglês misturados ao português geram termos nas duas línguas.</li>
  <li>A lista de palavras ignoradas foi feita à mão e pode deixar passar palavras genéricas.</li>
</ul>
</section>
"""

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Termos das Defesas</title>
<style>
:root{color-scheme:light;--bg:#fcfcfb;--card:#ffffff;--tx:#0b0b0b;--tx2:#52514e;--line:#dcdad4;--chip:#eef3fb;
 --s1:#2a78d6;--up:#11804f;--down:#c43c3b}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#1a1a19;--card:#222221;
 --tx:#f0efec;--tx2:#c3c2b7;--line:#3a3a38;--chip:#24303f;--s1:#3987e5;--up:#3fbf83;--down:#e66767}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#1a1a19;--card:#222221;--tx:#f0efec;--tx2:#c3c2b7;--line:#3a3a38;
 --chip:#24303f;--s1:#3987e5;--up:#3fbf83;--down:#e66767}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 system-ui,"Segoe UI",sans-serif}
main{max-width:900px;margin:0 auto;padding:32px 16px 64px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--tx2);margin:0 0 6px}
h1{font-size:28px;margin:0 0 6px;text-wrap:balance}h2{font-size:19px;margin:0 0 10px}h3{font-size:15px;margin:0 0 8px}
.sub,.nota{color:var(--tx2);font-size:13px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin:16px 0;overflow-x:auto}
.chart{width:100%;height:auto;display:block;font-size:12px}
.lbl{fill:var(--tx2)}.val{fill:var(--tx);font-variant-numeric:tabular-nums}.s1{fill:var(--s1)}
.tab{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
.tab th,.tab td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.tab thead th{color:var(--tx2);font-weight:600}.tab .n{text-align:right;white-space:nowrap}
.tab small{display:block;color:var(--tx2);font-weight:400}
.grupos th{width:11rem;font-weight:600}
.up{color:var(--up)}.down{color:var(--down)}
.chip{display:inline-flex;align-items:baseline;gap:5px;background:var(--chip);border-radius:999px;padding:2px 10px;margin:0 6px 6px 0;font-size:13px}
.chip small{color:var(--tx2);font-size:11px;font-variant-numeric:tabular-nums}
.duas{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:20px}
code{font-size:12px}
.formula{background:var(--chip);border-radius:8px;padding:12px 16px;margin:12px 0}
.formula p{margin:6px 0}.formula code{font-size:13px}
.passos li{margin:8px 0}.passos ul{margin:6px 0}.passos ul li{margin:4px 0}
.tab-wrap{overflow-x:auto}
section p{max-width:72ch}
</style></head><body><main>{{CORPO}}</main></body></html>"""

SAIDA_HTML.write_text(PAGINA.replace("{{CORPO}}", corpo), encoding="utf-8")
print(f"{N} defesas, {len(vocab)} termos.")
print(f"Relatório: {SAIDA_HTML}")
print(f"Termos por defesa: {SAIDA_CSV}")
