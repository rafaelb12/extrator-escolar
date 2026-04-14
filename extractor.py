import pandas as pd
import pdfplumber
import re
import unicodedata
import requests

# =========================================================
# BASE LOCAL DE NOMES
# =========================================================
nomes_femininos = {"MARIA","ANA","JULIA","BEATRIZ","SOFIA","ALICE","LAURA","LUIZA","RAFAELA","GABRIELA"}
nomes_masculinos = {"JOAO","JOSE","GABRIEL","LUCAS","PEDRO","MATEUS","RAFAEL","ENZO","MIGUEL","ARTHUR"}

cache_sexo = {}

# =========================================================
# FUNÇÕES UTILITÁRIAS
# =========================================================
def remover_acentos(texto):
    if not texto:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpar(texto):
    if not texto:
        return ""
    texto = texto.replace("\n", " ")
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip(" -,;")

def limpar_cpf(cpf):
    return re.sub(r'\D', '', cpf or "")

# =========================================================
# SEXO AUTOMÁTICO (API + CACHE)
# =========================================================
def inferir_sexo(nome):
    if not nome:
        return ""

    primeiro = remover_acentos(nome.split()[0].upper())

    if primeiro in nomes_femininos:
        return "F"
    if primeiro in nomes_masculinos:
        return "M"

    if primeiro in cache_sexo:
        return cache_sexo[primeiro]

    try:
        r = requests.get("https://api.genderize.io", params={"name": primeiro.lower()}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data["gender"] == "female" and data["probability"] >= 0.7:
                cache_sexo[primeiro] = "F"
                return "F"
            if data["gender"] == "male" and data["probability"] >= 0.7:
                cache_sexo[primeiro] = "M"
                return "M"
    except:
        pass

    cache_sexo[primeiro] = ""
    return ""

# =========================================================
# ETNIA
# =========================================================
def mapear_etnia(cor):
    cor = remover_acentos((cor or "").upper())
    if "BRANC" in cor: return "1"
    if "PRET" in cor: return "2"
    if "PARD" in cor: return "3"
    if "AMAREL" in cor: return "4"
    if "INDIGENA" in cor: return "5"
    return ""

# =========================================================
# EXTRAÇÃO PRINCIPAL
# =========================================================
def processar_pdf(caminho_pdf):
    texto_completo = ""

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            try:
                texto = pagina.extract_text(layout=True)
            except:
                texto = pagina.extract_text()

            if texto:
                texto_completo += texto + "\n"

    # separa alunos
    blocos = re.split(r"ALUNO:\s*", texto_completo)

    dados = []

    for bloco in blocos[1:]:
        bloco = limpar(bloco)

        nome = limpar(re.search(r"^(.*?)\s+CPF:", bloco).group(1)) if re.search(r"^(.*?)\s+CPF:", bloco) else ""

        cpf = limpar_cpf(re.search(r"CPF:\s*([\d\.\-]+)", bloco).group(1)) if re.search(r"CPF:", bloco) else ""

        nascimento = limpar(re.search(r"DATA:\s*([0-9/]+)", bloco).group(1)) if re.search(r"DATA:", bloco) else ""

        cidade = limpar(re.search(r"CIDADE:\s*(.*?)(EMAIL:|$)", bloco).group(1)) if re.search(r"CIDADE:", bloco) else ""

        bairro = limpar(re.search(r"BAIRRO:\s*(.*?)(ALUNO:|$)", bloco).group(1)) if re.search(r"BAIRRO:", bloco) else ""

        mae = limpar(re.search(r"M[ÃA]E:\s*(.*?)(PAI:|$)", bloco).group(1)) if re.search(r"M[ÃA]E:", bloco) else ""

        pai = limpar(re.search(r"PAI:\s*(.*?)(RG:|$)", bloco).group(1)) if re.search(r"PAI:", bloco) else ""

        etnia_raw = limpar(re.search(r"COR:\s*(.*?)(CIDADE:|$)", bloco).group(1)) if re.search(r"COR:", bloco) else ""
        etnia = mapear_etnia(etnia_raw)

        sexo = inferir_sexo(nome)

        # endereço simplificado
        endereco_match = re.search(r"DATA:.*?-\s*(.*?)(EMAIL:|BAIRRO:|$)", bloco)
        logradouro = ""
        numero = ""

        if endereco_match:
            endereco = limpar(endereco_match.group(1))

            num_match = re.search(r'(\d+|S/N)', endereco)
            if num_match:
                numero = num_match.group(1)
                logradouro = endereco.replace(numero, "").strip(" ,")
            else:
                logradouro = endereco

        if nome:
            dados.append({
                "nome": nome,
                "cpf": cpf,
                "nascimento": nascimento,
                "sexo": sexo,
                "logradouro": logradouro,
                "numero": numero,
                "bairro": bairro,
                "cidade": cidade,
                "estado": "CE",
                "etnia": etnia,
                "mae_nome": mae,
                "pai_nome": pai
            })

    df = pd.DataFrame(dados)

    df = df[df["nome"].str.strip() != ""]

    df = df.dropna(how="all")

    nome_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(nome_csv, index=False, encoding="utf-8-sig")

    return nome_csv
