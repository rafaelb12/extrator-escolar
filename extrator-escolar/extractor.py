import pandas as pd
import pdfplumber
import re
import os

def processar_pdf(caminho_pdf):
    dados_extraidos = []

    with pdfplumber.open(caminho_pdf) as pdf:
        texto_completo = ""
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_completo += texto + "\n"

    blocos = re.split(r"ALUNO:", texto_completo)

    for bloco in blocos[1:]:
        nome = re.search(r"(.*)", bloco)
        nome = nome.group(1).strip() if nome else ""

        dados_extraidos.append({
            "nome": nome
        })

    df = pd.DataFrame(dados_extraidos)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv