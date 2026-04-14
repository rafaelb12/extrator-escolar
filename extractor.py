import pdfplumber
import pandas as pd
import re
import unicodedata
import requests

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def inferir_sexo(nome):
    try:
        primeiro = remover_acentos(nome.split()[0].lower())

        r = requests.get("https://api.genderize.io", params={"name": primeiro}, timeout=3)
        if r.status_code == 200:
            genero = r.json().get("gender")
            if genero == "male":
                return "M"
            elif genero == "female":
                return "F"
    except:
        pass

    return ""

def processar_pdf(caminho_pdf):
    texto = ""

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto += pagina.extract_text() + "\n"

    blocos = re.split(r"\n\d+\n", texto)

    dados = []

    for bloco in blocos:
        linhas = [l.strip() for l in bloco.split("\n") if l.strip()]

        if len(linhas) < 8:
            continue

        try:
            nome = linhas[3]
            cpf = re.sub(r"\D", "", linhas[4])

            mae = linhas[5]
            pai = linhas[6]

            cidade = linhas[7]
            logradouro = linhas[8] if len(linhas) > 8 else ""
            bairro = linhas[9] if len(linhas) > 9 else ""

            nascimento_match = re.search(r"(\d{2}/\d{2}/\d{4})", bloco)
            nascimento = nascimento_match.group(1) if nascimento_match else ""

            sexo = inferir_sexo(nome)

            dados.append({
                "nome": nome,
                "cpf": cpf,
                "nascimento": nascimento,
                "mae_nome": mae,
                "pai_nome": pai,
                "cidade": cidade,
                "bairro": bairro,
                "logradouro": logradouro,
                "sexo": sexo,
                "etnia": ""
            })

        except:
            continue

    df = pd.DataFrame(dados)

    df = df.replace(r'\n', ' ', regex=True)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv
