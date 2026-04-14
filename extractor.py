import pdfplumber
import pandas as pd
import re
import unicodedata
import requests

# =========================
# FUNÇÕES BASE
# =========================
def limpar(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =========================
# SEXO AUTOMÁTICO (ONLINE)
# =========================
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

# =========================
# EXTRAÇÃO INTELIGENTE
# =========================
def processar_pdf(caminho_pdf):
    texto = ""

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto += pagina.extract_text() + "\n"

    # 🔥 DIVIDE POR ALUNO (PADRÃO DO PDF)
    blocos = re.split(r"\n\s*\d+\s*\n", texto)

    dados = []

    for bloco in blocos:
        bloco = bloco.strip()

        if len(bloco) < 50:
            continue

        try:
            # =========================
            # NOME (linha com mais palavras)
            # =========================
            linhas = bloco.split("\n")
            nome = max(linhas, key=lambda x: len(x.split()))

            # =========================
            # CPF
            # =========================
            cpf_match = re.search(r"\b\d{11}\b", bloco)
            cpf = cpf_match.group(0) if cpf_match else ""

            # =========================
            # DATA NASCIMENTO
            # =========================
            nasc_match = re.search(r"\d{2}/\d{2}/\d{4}", bloco)
            nascimento = nasc_match.group(0) if nasc_match else ""

            # =========================
            # MÃE e PAI (linhas próximas)
            # =========================
            mae = ""
            pai = ""

            for i, linha in enumerate(linhas):
                if nome in linha:
                    if i + 1 < len(linhas):
                        mae = linhas[i + 1]
                    if i + 2 < len(linhas):
                        pai = linhas[i + 2]
                    break

            # =========================
            # ENDEREÇO
            # =========================
            cidade = ""
            bairro = ""
            logradouro = ""

            for linha in linhas:
                if "ITAPIPOCA" in linha or "FORTALEZA" in linha:
                    cidade = linha

                if "SITIO" in linha or "AVENIDA" in linha or "PV" in linha:
                    logradouro = linha

                if "BARRENTO" in linha or "FLORES" in linha or "COQUEIRO" in linha:
                    bairro = linha

            sexo = inferir_sexo(nome)

            dados.append({
                "nome": limpar(nome),
                "cpf": cpf,
                "nascimento": nascimento,
                "mae_nome": limpar(mae),
                "pai_nome": limpar(pai),
                "cidade": limpar(cidade),
                "bairro": limpar(bairro),
                "logradouro": limpar(logradouro),
                "sexo": sexo,
                "etnia": ""
            })

        except:
            continue

    df = pd.DataFrame(dados)

    # 🔥 REMOVE BUG DE QUEBRA DE LINHA
    df = df.replace(r'\n', ' ', regex=True)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv
