import pdfplumber
import pandas as pd
import re
import unicodedata
import requests

# =========================
# UTIL
# =========================
def limpar(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

# =========================
# SEXO AUTOMÁTICO
# =========================
def inferir_sexo(nome):
    try:
        primeiro = remover_acentos(nome.split()[0].lower())

        r = requests.get("https://api.genderize.io", params={"name": primeiro}, timeout=3)

        if r.status_code == 200:
            genero = r.json().get("gender")
            prob = r.json().get("probability", 0)

            if genero == "male" and prob > 0.7:
                return "M"
            elif genero == "female" and prob > 0.7:
                return "F"
    except:
        pass

    return ""

# =========================
# PROCESSAR BLOCO (1 ALUNO)
# =========================
def processar_bloco(linhas):

    texto = " ".join(linhas)

    nome = max(linhas, key=lambda x: len(x.split()))

    cpf = re.search(r"\b\d{11}\b", texto)
    nascimento = re.search(r"\d{2}/\d{2}/\d{4}", texto)

    mae = ""
    pai = ""

    for i, linha in enumerate(linhas):
        if nome in linha:
            if i + 1 < len(linhas):
                mae = linhas[i + 1]
            if i + 2 < len(linhas):
                pai = linhas[i + 2]
            break

    cidade = ""
    bairro = ""
    logradouro = ""

    for linha in linhas:
        l = linha.upper()

        if any(c in l for c in ["ITAPIPOCA", "FORTALEZA", "ACARAU"]):
            cidade = linha

        if any(x in l for x in ["RUA", "AV", "SITIO", "PV"]):
            logradouro = linha

        if any(b in l for b in ["CENTRO", "COQUEIRO", "FLORES"]):
            bairro = linha

    sexo = inferir_sexo(nome)

    return {
        "nome": limpar(nome),
        "cpf": cpf.group(0) if cpf else "",
        "nascimento": nascimento.group(0) if nascimento else "",
        "mae_nome": limpar(mae),
        "pai_nome": limpar(pai),
        "cidade": limpar(cidade),
        "bairro": limpar(bairro),
        "logradouro": limpar(logradouro),
        "sexo": sexo,
        "etnia": ""
    }

# =========================
# PROCESSAR PDF
# =========================
def processar_pdf(caminho_pdf):

    dados = []

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:

            texto = pagina.extract_text()
            if not texto:
                continue

            linhas = texto.split("\n")

            bloco = []

            for linha in linhas:
                linha = linha.strip()

                # IGNORA LIXO
                if (
                    linha == ""
                    or "SIGE" in linha
                    or "ESCOLA" in linha
                    or "ENDEREÇO" in linha
                    or "ALUNO" in linha
                ):
                    continue

                # NOVO ALUNO
                if re.match(r"^\d{6,8}$", linha):
                    if bloco:
                        dados.append(processar_bloco(bloco))
                        bloco = []

                bloco.append(linha)

            if bloco:
                dados.append(processar_bloco(bloco))

    df = pd.DataFrame(dados)

    # 🔥 LIMPEZA FINAL (resolve seu bug)
    df = df.replace(r'[\r\n]+', ' ', regex=True)
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv
