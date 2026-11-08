"""Scraping das defesas (dissertações/teses) de um programa de pós-graduação no SIGAA/UFBA.

Uso (a partir da pasta principal): python scripts/scrape_defesas.py [id_programa]   (padrão: 1820)
Gera dados/defesas_<id>.xlsx e dados/defesas_<id>.csv.
"""
import codecs
import csv
import re
import sys
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

RAIZ = Path(__file__).resolve().parent.parent  # pasta principal do repositório
PROG_ID = sys.argv[1] if len(sys.argv) > 1 else "1820"
URL = f"https://sigaa.ufba.br/sigaa/public/programa/defesas.jsf?lc=pt_BR&id={PROG_ID}"


# A página mistura UTF-8 e Windows-1252; bytes inválidos em UTF-8 são lidos como cp1252.
def _cp1252_fallback(err):
    bad = err.object[err.start:err.end]
    return bad.decode("cp1252", errors="replace"), err.end


codecs.register_error("cp1252_fallback", _cp1252_fallback)


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", errors="cp1252_fallback")


def limpa(txt):
    txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", txt or "")
    return re.sub(r"\s+", " ", txt).strip()


def extrair(html):
    soup = BeautifulSoup(html, "html.parser")
    registros = []
    for bloco in soup.select("div#listagem_tabela"):
        grupo = bloco.select_one("#group_lt")
        ano = limpa(grupo.get_text()) if grupo else ""
        tipo = ""
        for tr in bloco.select("table#table_lt tr"):
            if "campos" in (tr.get("class") or []):
                tipo = limpa(tr.get_text())
                continue
            num = tr.select_one("td.tipoDefesa")
            if not num:
                continue
            ul = tr.find("ul")
            lis = ul.find_all("li", recursive=False)
            reg = {
                "Ano": ano, "Tipo": tipo, "Nº": limpa(num.get_text()),
                "Discente": "", "Título": "", "Orientador": "", "Banca": "",
                "Data": "", "Ata assinada": "", "Resumo": "", "Abstract": "",
            }
            banca, em_banca = [], False
            for li in lis:
                classes = li.get("class") or []
                texto = limpa(li.get_text(" "))
                if "txtResumo" in classes:
                    reg["Resumo"] = texto
                    continue
                if "txtResumoIngles" in classes:
                    reg["Abstract"] = texto
                    continue
                if li.select_one(".titulo_defesa"):
                    reg["Título"] = limpa(li.select_one(".titulo_defesa").get_text(" "))
                    continue
                b = li.find("b")
                rotulo = limpa(b.get_text()) if b else ""
                if rotulo.startswith("Data"):
                    m = re.search(r"\d{2}/\d{2}/\d{4}", texto)
                    reg["Data"] = m.group(0) if m else ""
                    ata = li.select_one("a.arquivoAtaAssinada")
                    if ata and ata.get("href"):
                        reg["Ata assinada"] = "https://sigaa.ufba.br" + ata["href"]
                    em_banca = False
                    continue
                if li.find("a") or not texto:
                    em_banca = False if li.find("a") else em_banca
                    continue
                if rotulo.startswith("Orientador"):
                    reg["Orientador"] = limpa(texto.split(":", 1)[1])
                elif rotulo.startswith("MEMBROS DA BANCA"):
                    em_banca = True
                elif b and not reg["Discente"]:
                    reg["Discente"] = rotulo
                elif em_banca:
                    banca.append(texto)
            reg["Banca"] = "; ".join(banca)
            registros.append(reg)
    return registros


def salvar(registros):
    cols = list(registros[0].keys())
    (RAIZ / "dados").mkdir(exist_ok=True)
    base = str(RAIZ / "dados" / f"defesas_{PROG_ID}")
    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
        w.writeheader()
        w.writerows(registros)

    wb = Workbook()
    ws = wb.active
    ws.title = "Defesas"
    ws.append(cols)
    for r in registros:
        ws.append([r[c] for c in cols])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E78")
    larguras = {"Ano": 7, "Tipo": 14, "Nº": 5, "Discente": 32, "Título": 60,
                "Orientador": 32, "Banca": 60, "Data": 11, "Ata assinada": 30, "Resumo": 80, "Abstract": 80}
    for i, c in enumerate(cols, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = larguras.get(c, 20)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=False, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    resumo = wb.create_sheet("Resumo por ano")
    resumo.append(["Ano", "Tipo", "Quantidade"])
    cont = {}
    for r in registros:
        cont[(r["Ano"], r["Tipo"])] = cont.get((r["Ano"], r["Tipo"]), 0) + 1
    for (ano, tipo), q in sorted(cont.items(), reverse=True):
        resumo.append([ano, tipo, q])
    for c in resumo[1]:
        c.font = Font(bold=True)
    wb.save(base + ".xlsx")
    return base


if __name__ == "__main__":
    regs = extrair(baixar(URL))
    if not regs:
        sys.exit("Nenhuma defesa encontrada.")
    base = salvar(regs)
    print(f"{len(regs)} defesas salvas em {base}.xlsx e {base}.csv")
