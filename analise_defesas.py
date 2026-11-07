"""Análise básica das defesas (dissertações/teses) extraídas do SIGAA/UFBA.

Uso: python analise_defesas.py [arquivo.csv]   (padrão: defesas_1820.csv)
Gera relatorio_defesas.html (abre em qualquer navegador; dá para imprimir em PDF).
Depende apenas de pandas.
"""
import html
import re
import sys
import unicodedata
from collections import Counter
from datetime import date

import pandas as pd

ARQ = sys.argv[1] if len(sys.argv) > 1 else "defesas_1820.csv"
SAIDA = "relatorio_defesas.html"
TIPOS = ["Dissertações", "Teses"]
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

STOP = set("""
a o e de da do das dos em no na nos nas um uma uns umas para por com sem sobre entre
ao aos à às que se seu sua seus suas como mais ou baseado baseada baseados baseadas
uso utilizando usando partir através meio via estudo abordagem análise caso proposta
the of and in for to on a an with from by using based towards toward its at into via
approach study analysis case proposal
""".split())
EN_MARK = {"the", "of", "and", "for", "with", "using", "based", "towards", "an", "on", "in", "to"}
PT_MARK = {"de", "da", "do", "para", "uma", "um", "com", "em", "dos", "das", "e", "na", "no"}


# ---------- utilidades ----------
def chave_nome(n):
    """Normaliza nome (maiúsculas, sem acento) para agrupar grafias diferentes."""
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", n).strip().upper()


def nome_bonito(n):
    minus = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p.lower() if p.lower() in minus else p.capitalize() for p in str(n).split())


def idioma(titulo):
    pal = re.findall(r"[a-zà-ú]+", titulo.lower())
    en = sum(p in EN_MARK for p in pal)
    pt = sum(p in PT_MARK for p in pal)
    if en > pt:
        return "Inglês"
    if pt > en:
        return "Português"
    # títulos curtos sem conectivos: usa acentuação como pista
    return "Português" if re.search(r"[ãõçáéíóúâêô]", titulo.lower()) else "Inglês"


def esc(x):
    return html.escape(str(x))


# ---------- gráficos SVG (sem dependências) ----------
def svg_colunas_empilhadas(categorias, series, nomes, largura=720, altura=280):
    """Colunas empilhadas: series = lista de listas (uma por tipo)."""
    ml, mr, mt, mb = 36, 10, 14, 28
    w, h = largura - ml - mr, altura - mt - mb
    totais = [sum(s[i] for s in series) for i in range(len(categorias))]
    vmax = max(totais) or 1
    passo = 10 if vmax <= 60 else 20
    topo = ((vmax // passo) + 1) * passo
    bw = w / len(categorias)
    barra = min(38, bw * 0.62)
    out = [f'<svg viewBox="0 0 {largura} {altura}" role="img" class="chart">']
    for v in range(0, topo + 1, passo):
        y = mt + h - v / topo * h
        out.append(f'<line x1="{ml}" x2="{ml + w}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" class="tick" text-anchor="end">{v}</text>')
    for i, cat in enumerate(categorias):
        x = ml + i * bw + (bw - barra) / 2
        base = mt + h
        for k, s in enumerate(series):
            v = s[i]
            if not v:
                continue
            bh = v / topo * h
            y = base - bh
            topo_seg = k == len(series) - 1 or all(series[j][i] == 0 for j in range(k + 1, len(series)))
            r = 4 if topo_seg else 0
            gap = 0 if k == 0 else 2
            out.append(
                f'<path d="{_ret(x, y, barra, bh - gap, r)}" class="s{k + 1}">'
                f"<title>{esc(cat)} · {esc(nomes[k])}: {v}</title></path>"
            )
            base = y
        out.append(f'<text x="{x + barra / 2:.1f}" y="{base - 5:.1f}" class="val" text-anchor="middle">{totais[i]}</text>')
        out.append(f'<text x="{x + barra / 2:.1f}" y="{mt + h + 18}" class="tick" text-anchor="middle">{esc(cat)}</text>')
    out.append("</svg>")
    return "".join(out)


def _ret(x, y, w, h, r):
    """Retângulo com cantos superiores arredondados (base reta)."""
    h = max(h, 0.5)
    r = min(r, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"H{x + w - r:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z")


def svg_barras_h(rotulos, valores, largura=720, sufixo=""):
    """Barras horizontais de uma série só."""
    lin, ml, mr = 26, 260, 50
    altura = lin * len(rotulos) + 8
    w = largura - ml - mr
    vmax = max(valores) or 1
    out = [f'<svg viewBox="0 0 {largura} {altura}" role="img" class="chart">']
    for i, (r, v) in enumerate(zip(rotulos, valores)):
        y = 4 + i * lin
        bw = v / vmax * w
        out.append(f'<text x="{ml - 8}" y="{y + 15}" class="lbl" text-anchor="end">{esc(r)}</text>')
        out.append(
            f'<path d="M{ml},{y + 4} H{ml + bw - 4:.1f} Q{ml + bw:.1f},{y + 4} {ml + bw:.1f},{y + 8} '
            f'V{y + 16} Q{ml + bw:.1f},{y + 20} {ml + bw - 4:.1f},{y + 20} H{ml} Z" class="s1">'
            f"<title>{esc(r)}: {v}{sufixo}</title></path>"
        )
        out.append(f'<text x="{ml + bw + 6:.1f}" y="{y + 16}" class="val">{v}{sufixo}</text>')
    out.append("</svg>")
    return "".join(out)


def tabela(df, idx=False):
    return df.to_html(index=idx, border=0, classes="tab", escape=True)


# ---------- análise ----------
def main():
    d = pd.read_csv(ARQ, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    d["Ano"] = d["Ano"].astype(int)
    d["Data_dt"] = pd.to_datetime(d["Data"], format="%d/%m/%Y", errors="coerce")
    d["Mes"] = d["Data_dt"].dt.month
    d["Orient_key"] = d["Orientador"].map(chave_nome)
    d["Banca_lista"] = d["Banca"].map(lambda s: [m.strip() for m in s.split(";") if m.strip()])
    d["Tam_banca"] = d["Banca_lista"].map(len)
    d["Palavras_resumo"] = d["Resumo"].map(lambda s: len(s.split()))
    d["Idioma_titulo"] = d["Título"].map(idioma)

    total = len(d)
    n_tipo = d["Tipo"].value_counts()
    anos = list(range(d["Ano"].min(), d["Ano"].max() + 1))
    ano_min, ano_max = anos[0], anos[-1]
    anos_completos = [a for a in anos if a not in (ano_min,)]  # 1º ano tem só 1 defesa

    # 1. por ano e tipo
    pivo = (d.pivot_table(index="Ano", columns="Tipo", values="Discente", aggfunc="count")
              .reindex(index=anos, columns=TIPOS).fillna(0).astype(int))
    pivo["Total"] = pivo.sum(axis=1)
    ano_pico = int(pivo["Total"].idxmax())
    media_ano = pivo.loc[anos_completos, "Total"].mean()
    graf_ano = svg_colunas_empilhadas([str(a) for a in anos],
                                      [pivo[t].tolist() for t in TIPOS], TIPOS)

    # 2. por mês
    por_mes = d["Mes"].value_counts().reindex(range(1, 13)).fillna(0).astype(int)
    graf_mes = svg_colunas_empilhadas(
        MESES,
        [d[d.Tipo == t]["Mes"].value_counts().reindex(range(1, 13)).fillna(0).astype(int).tolist() for t in TIPOS],
        TIPOS)
    mes_pico = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto",
                "Setembro", "Outubro", "Novembro", "Dezembro"][int(por_mes.idxmax()) - 1]

    # 3. orientadores
    nomes_orient = d.groupby("Orient_key")["Orientador"].agg(lambda s: s.mode()[0])
    orient = (d.groupby(["Orient_key", "Tipo"]).size().unstack(fill_value=0)
                .reindex(columns=TIPOS, fill_value=0))
    orient["Total"] = orient.sum(axis=1)
    orient = orient.sort_values(["Total", "Teses"], ascending=False)
    n_orient = len(orient)
    top_or = orient.head(15).copy()
    top_or.index = [nome_bonito(nomes_orient[k]) for k in top_or.index]
    graf_or = svg_barras_h(top_or.index.tolist(), top_or["Total"].tolist())
    top5_share = orient["Total"].head(5).sum() / total * 100
    orient_1 = (orient["Total"] == 1).sum()

    # 4. banca
    banca_tipo = d.groupby("Tipo")["Tam_banca"].agg(["mean", "min", "max"]).reindex(TIPOS)
    membros = Counter()
    grafia = {}
    for _, r in d.iterrows():
        for m in r["Banca_lista"]:
            k = chave_nome(m)
            if k != r["Orient_key"]:  # exclui o próprio orientador
                membros[k] += 1
                grafia.setdefault(k, m)
    orient_na_banca = sum(r["Orient_key"] in {chave_nome(m) for m in r["Banca_lista"]}
                          for _, r in d.iterrows()) / total * 100
    chaves_orient = set(orient.index)
    top_mem = membros.most_common(15)
    graf_mem = svg_barras_h([nome_bonito(grafia[k]) for k, _ in top_mem], [v for _, v in top_mem])
    n_membros = len(membros)
    externos = sum(1 for k in membros if k not in chaves_orient)

    # 5. títulos
    palavras = Counter()
    for t in d["Título"]:
        for p in re.findall(r"[a-zà-úA-ZÀ-Ú0-9\-]+", t.lower()):
            if len(p) > 2 and p not in STOP:
                palavras[p] += 1
    top_pal = palavras.most_common(20)
    graf_pal = svg_barras_h([p for p, _ in top_pal], [v for _, v in top_pal])
    idioma_ano = (d.pivot_table(index="Ano", columns="Idioma_titulo", values="Discente", aggfunc="count")
                    .reindex(index=anos).fillna(0).astype(int))
    pct_en = (d["Idioma_titulo"] == "Inglês").mean() * 100
    en_ano = (idioma_ano.get("Inglês", 0) / idioma_ano.sum(axis=1) * 100).round(0).astype(int)
    graf_en = svg_barras_h([str(a) for a in anos], en_ano.tolist(), sufixo="%")

    # 6. resumos
    resumo_tipo = d.groupby("Tipo")["Palavras_resumo"].agg(["mean", "median", "min", "max"]).reindex(TIPOS)

    # 7. qualidade dos dados
    vazios = {c: int((d[c] == "").sum()) for c in
              ["Discente", "Título", "Orientador", "Banca", "Data", "Resumo", "Abstract", "Ata assinada"]}

    # ---------- montagem do relatório ----------
    t_ano = pivo.reset_index().rename(columns={"Ano": "Ano"})
    t_or = top_or.reset_index().rename(columns={"index": "Orientador"})
    t_banca = banca_tipo.round(1).rename(columns={"mean": "Média", "min": "Mín.", "max": "Máx."}).reset_index()
    t_res = resumo_tipo.round(0).astype(int).rename(
        columns={"mean": "Média", "median": "Mediana", "min": "Mín.", "max": "Máx."}).reset_index()
    rotulos = {"Resumo": "Resumo (português)", "Abstract": "Abstract (resumo em inglês)",
               "Ata assinada": "Link da ata assinada"}
    t_vaz = pd.DataFrame({
        "Campo": [rotulos.get(c, c) for c in vazios],
        "Preenchidos": [total - v for v in vazios.values()],
        "Vazios": list(vazios.values()),
        "% preenchido": [f"{(total - v) / total * 100:.1f}%".replace(".", ",") for v in vazios.values()],
    })

    tiles = [
        (total, "defesas no total"),
        (int(n_tipo.get("Dissertações", 0)), "dissertações"),
        (int(n_tipo.get("Teses", 0)), "teses"),
        (n_orient, "orientadores"),
        (f"{media_ano:.0f}", f"defesas/ano ({anos_completos[0]}–{ano_max})"),
    ]
    tiles_html = "".join(f'<div class="tile"><b>{esc(v)}</b><span>{esc(l)}</span></div>' for v, l in tiles)

    legenda = ('<div class="leg"><span><i class="s1"></i>Dissertações</span>'
               '<span><i class="s2"></i>Teses</span></div>')

    corpo = f"""
<header>
  <h1>Defesas de pós-graduação — análise básica</h1>
  <p class="sub">Fonte: SIGAA/UFBA, página pública de defesas do programa (id 1820) · arquivo <code>{esc(ARQ)}</code>
  · {total} registros, {ano_min}–{ano_max} · gerado em {date.today():%d/%m/%Y}</p>
</header>

<div class="tiles">{tiles_html}</div>

<section>
<h2>1. Destaques</h2>
<ul class="dest">
  <li>O programa registra <b>{total}</b> defesas: <b>{n_tipo.get('Dissertações', 0)}</b> dissertações
      ({n_tipo.get('Dissertações', 0) / total * 100:.0f}%) e <b>{n_tipo.get('Teses', 0)}</b> teses
      ({n_tipo.get('Teses', 0) / total * 100:.0f}%).</li>
  <li>O ano com mais defesas foi <b>{ano_pico}</b> ({pivo.loc[ano_pico, 'Total']}). {ano_min} tem só
      {pivo.loc[ano_min, 'Total']} defesa, por isso ficou fora da média anual.
      As teses aparecem a partir de {int(d[d.Tipo == 'Teses']['Ano'].min())}.</li>
  <li><b>{mes_pico}</b> é o mês com mais defesas ({por_mes.max()}), acompanhando o fim de semestre.</li>
  <li>Os 5 orientadores mais ativos respondem por <b>{top5_share:.0f}%</b> das defesas;
      {orient_1} dos {n_orient} orientadores aparecem em uma única defesa.</li>
  <li>Em média, a banca tem <b>{banca_tipo.loc['Dissertações', 'mean']:.1f}</b> membros nas dissertações e
      <b>{banca_tipo.loc['Teses', 'mean']:.1f}</b> nas teses. O orientador consta na banca em
      {orient_na_banca:.0f}% dos casos.</li>
  <li><b>{pct_en:.0f}%</b> dos títulos estão em inglês (classificação automática, aproximada).</li>
</ul>
</section>

<section>
<h2>2. Defesas por ano</h2>
{legenda}{graf_ano}
<details><summary>Ver tabela</summary>{tabela(t_ano)}</details>
<p class="nota">{ano_max} considera as defesas publicadas até a data da coleta.</p>
</section>

<section>
<h2>3. Distribuição por mês</h2>
<p class="nota">Todos os anos somados, pela data da defesa.</p>
{legenda}{graf_mes}
</section>

<section>
<h2>4. Orientadores com mais defesas (top 15)</h2>
{graf_or}
<details><summary>Ver tabela</summary>{tabela(t_or)}</details>
</section>

<section>
<h2>5. Bancas</h2>
<h3>Tamanho da banca por tipo</h3>
{tabela(t_banca)}
<h3>Membros que mais participam de bancas (top 15, sem contar o próprio orientador)</h3>
{graf_mem}
<p class="nota">{n_membros} pessoas diferentes participaram de bancas como não orientadoras;
{externos} delas nunca aparecem como orientadoras no programa, o que indica participação externa.</p>
</section>

<section>
<h2>6. Temas: palavras mais frequentes nos títulos</h2>
<p class="nota">Palavras com mais de 2 letras, sem artigos e preposições (PT/EN).</p>
{graf_pal}
<h3>Títulos em inglês por ano</h3>
{graf_en}
</section>

<section>
<h2>7. Resumos (número de palavras)</h2>
{tabela(t_res)}
</section>

<section>
<h2>8. Qualidade dos dados</h2>
{tabela(t_vaz)}
<p class="nota">Todas as {total} defesas têm resumo em português. O único abstract vazio é o de
{esc(", ".join(d.loc[d["Abstract"] == "", "Discente"].map(nome_bonito)) or "—")}: no próprio SIGAA o campo está em branco.
O link da ata assinada só existe nas defesas que o publicaram no SIGAA. Nomes foram agrupados
sem acento e sem diferença de maiúsculas, porque o sistema usa grafias diferentes para a mesma pessoa.</p>
</section>
"""
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(PAGINA.replace("{{CORPO}}", corpo))
    print(f"Relatório salvo em {SAIDA}")


PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório de Defesas</title>
<style>
:root{color-scheme:light;--bg:#fcfcfb;--card:#ffffff;--tx:#0b0b0b;--tx2:#52514e;--grid:#e6e5e1;
 --line:#dcdad4;--s1:#2a78d6;--s2:#eb6834}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#1a1a19;
 --card:#222221;--tx:#f0efec;--tx2:#c3c2b7;--grid:#333331;--line:#3a3a38;--s1:#3987e5;--s2:#d95926}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#1a1a19;--card:#222221;--tx:#f0efec;--tx2:#c3c2b7;
 --grid:#333331;--line:#3a3a38;--s1:#3987e5;--s2:#d95926}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.55 system-ui,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:0 0 12px}h3{font-size:15px;margin:18px 0 8px}
.sub,.nota{color:var(--tx2);font-size:13px}
section{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px;margin:16px 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:20px 0}
.tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.tile b{display:block;font-size:26px;font-variant-numeric:tabular-nums}.tile span{color:var(--tx2);font-size:13px}
.dest li{margin:6px 0}
.chart{width:100%;height:auto;display:block;font-size:12px}
.grid{stroke:var(--grid);stroke-width:1}
.tick,.lbl{fill:var(--tx2)}.val{fill:var(--tx);font-variant-numeric:tabular-nums}
.s1{fill:var(--s1)}.s2{fill:var(--s2)}path.s1:hover,path.s2:hover{opacity:.8}
.leg{display:flex;gap:16px;font-size:13px;color:var(--tx2);margin-bottom:6px}
.leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.leg i.s1{background:var(--s1)}.leg i.s2{background:var(--s2)}
.tab{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums;margin:8px 0}
.tab th,.tab td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left}
.tab th{color:var(--tx2);font-weight:600}
details{margin-top:8px}summary{cursor:pointer;color:var(--tx2);font-size:13px}
code{font-size:12px}
@media print{section{break-inside:avoid}details{display:block}}
</style></head><body><main>{{CORPO}}</main></body></html>"""

if __name__ == "__main__":
    main()
