"""Prepara o arquivo de dados do dashboard a partir do CSV do scraping.

Uso: python gerar_dados_dashboard.py [defesas_1820.csv]
Gera defesas_dashboard.json: uma linha por defesa, com nomes padronizados
(mesma pessoa escrita de formas diferentes vira um nome só) e campos auxiliares.
"""
import json
import re
import sys
import unicodedata
from collections import Counter

import pandas as pd

ARQ = sys.argv[1] if len(sys.argv) > 1 else "defesas_1820.csv"
SAIDA = "defesas_dashboard.json"

EN_MARK = {"the", "of", "and", "for", "with", "using", "based", "towards", "an", "on", "in", "to"}
PT_MARK = {"de", "da", "do", "para", "uma", "um", "com", "em", "dos", "das", "e", "na", "no"}


def chave(n):
    n = unicodedata.normalize("NFKD", str(n)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", n).strip().upper()


def bonito(n):
    minus = {"de", "da", "do", "das", "dos", "e"}
    return " ".join(p.lower() if p.lower() in minus else p.capitalize() for p in str(n).split())


def idioma(t):
    pal = re.findall(r"[a-zà-ú]+", t.lower())
    en, pt = sum(p in EN_MARK for p in pal), sum(p in PT_MARK for p in pal)
    if en != pt:
        return "Inglês" if en > pt else "Português"
    return "Português" if re.search(r"[ãõçáéíóúâêô]", t.lower()) else "Inglês"


d = pd.read_csv(ARQ, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
d["banca_l"] = d["Banca"].map(lambda s: [m.strip() for m in s.split(";") if m.strip()])

# grafia mais comum de cada pessoa (orientadores e membros de banca juntos)
grafias = {}
for _, r in d.iterrows():
    for n in [r["Orientador"], *r["banca_l"]]:
        grafias.setdefault(chave(n), Counter())[n] += 1
canon = {k: bonito(c.most_common(1)[0][0]) for k, c in grafias.items()}

linhas = []
for _, r in d.iterrows():
    dia, mes, ano_d = r["Data"].split("/")
    ko = chave(r["Orientador"])
    chaves_banca = [chave(m) for m in r["banca_l"]]
    linhas.append({
        "id": f"{r['Ano']}-{'T' if r['Tipo'] == 'Teses' else 'D'}-{int(r['Nº']):02d}",
        "ano": int(r["Ano"]),
        "tipo": "Tese" if r["Tipo"] == "Teses" else "Dissertação",
        "data": r["Data"],
        "data_iso": f"{ano_d}-{mes}-{dia}",
        "mes": int(mes),
        "discente": bonito(r["Discente"]),
        "titulo": r["Título"],
        "orientador": canon[ko],
        "banca": "; ".join(canon[k] for k in chaves_banca),
        "membros": [canon[k] for k in chaves_banca if k != ko],
        "orientador_na_banca": ko in chaves_banca,
        "tam_banca": len(chaves_banca),
        "palavras_resumo": len(r["Resumo"].split()),
        "idioma_titulo": idioma(r["Título"]),
        "resumo": r["Resumo"],
        "abstract": r["Abstract"],
        "ata_url": r["Ata assinada"],
    })

with open(SAIDA, "w", encoding="utf-8") as f:
    json.dump(linhas, f, ensure_ascii=False)
print(f"{len(linhas)} defesas salvas em {SAIDA}")
