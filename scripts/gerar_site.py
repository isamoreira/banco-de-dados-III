"""Gera dashboard.html, a versão do dashboard que funciona fora do Claude (GitHub Pages).

Uso (a partir da pasta principal): python scripts/gerar_site.py
Lê scripts/dashboard_index.html (o mesmo código do dashboard publicado no Claude), acrescenta o
visual (cores, fontes, espaçamentos) e um pequeno motor que carrega defesas_dashboard.json
e aplica os filtros. Gera dashboard.html na pasta principal, ao lado de defesas_dashboard.json.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent  # pasta principal do repositório

ORIGEM = RAIZ / "scripts" / "dashboard_index.html"
SAIDA = RAIZ / "dashboard.html"
DADOS = "defesas_dashboard.json"

corpo = open(ORIGEM, encoding="utf-8").read()
corpo = re.sub(r'<meta name="dash-one-writer">\s*', "", corpo)

HEAD = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Defesas de pós-graduação UFBA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&display=swap">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<style>
  :root {
    color-scheme: light;
    --font-anthropic-sans: "Source Sans 3", system-ui, "Segoe UI", sans-serif;
    --font-anthropic-serif: "Source Serif 4", Georgia, "Times New Roman", serif;
    --color-bg: #f7f7f5;
    --color-panel: #ffffff;
    --color-fg: #1b1c1f;
    --color-fg-muted: #5c5f66;
    --color-border-line: #e2e2de;
    --color-bad: #c43c3b;
    --cds-text-secondary: #5c5f66;
    --cds-surface-popover: #ffffff;
    --cds-border: #d6d6d1;
    --cds-shadow-popover: 0 8px 24px rgba(20, 22, 28, .14);
    --cds-chart-grid: #ececea;
    --cds-chart-axis: #c8c8c3;
    --cds-radius: 8px;
    --cds-gap-xs: 4px; --cds-gap-sm: 8px; --cds-gap-md: 14px; --cds-gap-lg: 22px; --cds-gap-xl: 32px;
    --cds-pad-xs: 4px; --cds-pad-sm: 8px; --cds-pad-md: 14px; --cds-pad-lg: 18px; --cds-pad-xl: 28px;
    --cds-font-size-caption: 13px; --cds-font-size-body: 15px; --cds-font-size-heading: 17px; --cds-font-size-title: 30px;
    --cds-font-weight-medium: 600;
    --cds-dur-slow: .3s;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --color-bg: #161718; --color-panel: #1f2022; --color-fg: #eeeeec; --color-fg-muted: #a9abb0;
      --color-border-line: #333538; --color-bad: #e66767; --cds-text-secondary: #a9abb0;
      --cds-surface-popover: #26282b; --cds-border: #3d4044; --cds-shadow-popover: 0 8px 24px rgba(0, 0, 0, .5);
      --cds-chart-grid: #2c2e31; --cds-chart-axis: #4a4d52;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --color-bg: #161718; --color-panel: #1f2022; --color-fg: #eeeeec; --color-fg-muted: #a9abb0;
    --color-border-line: #333538; --color-bad: #e66767; --cds-text-secondary: #a9abb0;
    --cds-surface-popover: #26282b; --cds-border: #3d4044; --cds-shadow-popover: 0 8px 24px rgba(0, 0, 0, .5);
    --cds-chart-grid: #2c2e31; --cds-chart-axis: #4a4d52;
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body { margin: 0; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); font-size: var(--cds-font-size-body); line-height: 1.5; }
  #dash-root { max-width: 1180px; margin-inline: auto; padding-block: 28px 56px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
  [hidden] { display: none !important; }
  .dash-select { font: inherit; font-size: var(--cds-font-size-body); color: var(--color-fg); background-color: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); height: 36px; padding: 0 30px 0 10px; appearance: none; -webkit-appearance: none; cursor: pointer;
    background-image: linear-gradient(45deg, transparent 50%, currentColor 50%), linear-gradient(135deg, currentColor 50%, transparent 50%);
    background-position: calc(100% - 15px) 50%, calc(100% - 10px) 50%; background-size: 5px 5px; background-repeat: no-repeat; }
  .dash-select:focus-visible { outline: 2px solid var(--color-fg); outline-offset: 2px; }
  .df-btn { height: 36px; }
  .df-erro { background: var(--color-panel); border: 1px solid var(--color-border-line); border-radius: var(--cds-radius); padding: 14px 18px; color: var(--color-fg); }
  .df-erro b { color: var(--color-bad); }
  .df-fonte { margin-top: 28px; font-size: 13px; color: var(--color-fg-muted); }
</style>
<script>
  // Motor mínimo que imita a API do dashboard do Claude (dash.*) para rodar no GitHub Pages.
  window.dash = (() => {
    const estado = { status: 'loading', data: [], message: '' };
    const padrao = { ano: '', tipo: '', orientador: '' };
    let params = { ...padrao };
    const desenhos = new Map();
    const ouvintes = [];
    const escuro = window.matchMedia('(prefers-color-scheme: dark)');
    const ehEscuro = () => document.documentElement.dataset.theme === 'dark' || (document.documentElement.dataset.theme !== 'light' && escuro.matches);
    const rodarDesenho = (nome) => {
      const fn = desenhos.get(nome);
      if (!fn) return;
      document.querySelectorAll(`[data-draw="${nome}"]`).forEach((el) => {
        if (el.closest('[hidden]')) return;
        try { fn(el); } catch (e) { console.error(`Erro no desenho "${nome}":`, e); }
      });
    };
    const rodarTudo = () => {
      ouvintes.forEach((fn) => { try { fn(); } catch (e) { console.error(e); } });
      desenhos.forEach((_, nome) => rodarDesenho(nome));
    };
    const api = {
      data: () => estado,
      params: () => ({ ...params }),
      setParams(p) { Object.entries(p).forEach(([k, v]) => { params[k] = v ?? ''; }); api._hash(); rodarTudo(); },
      resetParams() { params = { ...padrao }; api._hash(); rodarTudo(); },
      draw(nome, fn) { if (fn) desenhos.set(nome, fn); else rodarDesenho(nome); },
      onData(fn) { ouvintes.push(fn); try { fn(); } catch (e) { console.error(e); } },
      setLink(nome) { history.replaceState(null, '', '#' + nome); },
      get colors() { return ehEscuro() ? ['#3987e5', '#d95926'] : ['#2a78d6', '#eb6834']; },
      _hash() {},
      async _iniciar(url) {
        rodarTudo();
        try {
          const r = await fetch(url, { cache: 'no-cache' });
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          estado.data = await r.json();
          estado.status = 'ok';
        } catch (e) {
          estado.status = 'error';
          estado.message = String(e.message || e);
          const caixa = document.getElementById('dash-root');
          const aviso = document.createElement('div');
          aviso.className = 'df-erro';
          aviso.innerHTML = '<b>Não foi possível carregar os dados.</b> Confira se o arquivo <code>' + url + '</code> está na mesma pasta que esta página. Abrindo o arquivo direto do computador (file://) o navegador bloqueia a leitura; use o GitHub Pages ou um servidor local.';
          caixa.prepend(aviso);
        }
        rodarTudo();
        // redesenha ao trocar de aba, ao mudar o tamanho da janela e ao trocar o tema
        const mo = new MutationObserver(rodarTudo);
        document.querySelectorAll('[data-pagina]').forEach((s) => mo.observe(s, { attributes: true, attributeFilter: ['hidden'] }));
        let t;
        window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(rodarTudo, 150); });
        escuro.addEventListener('change', rodarTudo);
      },
    };
    return api;
  })();
</script>
</head>
<body>
<div id="dash-root">
"""

FOOT = f"""
<p class="df-fonte">Fonte: página pública de defesas do SIGAA/UFBA (programa id 1820), coletada por scraping. Dados em <a href="{DADOS}" style="color:inherit">{DADOS}</a>.</p>
</div>
<script>dash._iniciar('{DADOS}');</script>
</body>
</html>
"""

with open(SAIDA, "w", encoding="utf-8") as f:
    f.write(HEAD + corpo + FOOT)
print(f"Gerado {SAIDA.name} (usa {DADOS}, na mesma pasta).")
