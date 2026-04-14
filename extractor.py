import pandas as pd
import pdfplumber
import re
import os
import unicodedata
import requests

# ==============================
# FUNÇÕES BASE
# ==============================

def limpar_texto(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def remover_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def limpar_cpf(cpf):
    return re.sub(r'\D', '', cpf or "")

def extrair(padrao, texto):
    match = re.search(padrao, texto, re.IGNORECASE)
    return limpar_texto(match.group(1)) if match else ""

# ==============================
# SEXO AUTOMÁTICO (API)
# ==============================

cache_sexo = {}

def inferir_sexo(nome):
    if not nome:
        return ""

    primeiro = remover_acentos(nome.split()[0].lower())

    if primeiro in cache_sexo:
        return cache_sexo[primeiro]

    try:
        r = requests.get(
            "https://api.genderize.io",
            params={"name": primeiro},
            timeout=3
        )

        if r.status_code == 200:
            data = r.json()
            if data["gender"] == "male":
                cache_sexo[primeiro] = "M"
                return "M"
            elif data["gender"] == "female":
                cache_sexo[primeiro] = "F"
                return "F"

    except:
        pass

    cache_sexo[primeiro] = ""
    return ""

# ==============================
# ETNIA
# ==============================

def mapear_etnia(cor):
    cor = remover_acentos(cor.upper())

    if "BRANC" in cor: return "1"
    if "PRET" in cor: return "2"
    if "PARD" in cor: return "3"
    if "AMAREL" in cor: return "4"
    if "INDIGENA" in cor: return "5"
    return ""

# ==============================
# PROCESSAMENTO PRINCIPAL
# ==============================

def processar_pdf(caminho_pdf):

    dados = []

    with pdfplumber.open(caminho_pdf) as pdf:
        texto = ""
        for pagina in pdf.pages:
            t = pagina.extract_text()
            if t:
                texto += t + "\n"

    blocos = re.split(r"ALUNO:\s+", texto)

    for bloco in blocos[1:]:
        try:
            nome = extrair(r"^(.*?)\s+(CPF|DATA)", bloco)
            cpf = limpar_cpf(extrair(r"CPF:\s*([\d\.\-]+)", bloco))
            nascimento = extrair(r"(\d{2}/\d{2}/\d{4})", bloco)
            mae = extrair(r"M[ÃA]E:\s*(.*?)(?:PAI:|$)", bloco)
            pai = extrair(r"PAI:\s*(.*?)(?:RG|$)", bloco)
            cidade = extrair(r"CIDADE:\s*(.*)", bloco)
            bairro = extrair(r"BAIRRO:\s*(.*)", bloco)
            etnia_raw = extrair(r"COR:\s*(.*)", bloco)

            sexo = inferir_sexo(nome)
            etnia = mapear_etnia(etnia_raw)

            logradouro = extrair(r"\d{2}/\d{2}/\d{4}\s*-\s*(.*)", bloco)

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
                "etnia": etnia
            })

        except Exception as e:
            print("Erro ao processar aluno:", e)

    df = pd.DataFrame(dados)

    # 🔥 CORREÇÃO PRINCIPAL DO CSV
    nome_saida = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(nome_saida, index=False, encoding="utf-8-sig")

    return nome_saida
