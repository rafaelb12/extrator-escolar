import pandas as pd
import pdfplumber
import re
import requests
import unicodedata

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn') if texto else ""

def limpar_texto(texto):
    return re.sub(r'\s+', ' ', texto).strip() if texto else ""

def limpar_cpf(cpf):
    return re.sub(r'\D', '', cpf or "")


cache_sexo = {}

nomes_femininos = {"MARIA", "ANA", "JULIA", "BEATRIZ", "SOFIA", "ALICE", "MANUELA", "HELENA"}
nomes_masculinos = {"JOAO", "JOSE", "GABRIEL", "LUCAS", "PEDRO", "RAFAEL", "MIGUEL", "ARTHUR"}

def inferir_sexo(nome):
    if not nome:
        return ""

    primeiro = remover_acentos(nome.split()[0].upper())

    # Base local (rápido)
    if primeiro in nomes_femininos:
        return "F"
    if primeiro in nomes_masculinos:
        return "M"

    # Cache
    if primeiro in cache_sexo:
        return cache_sexo[primeiro]

    # API online
    try:
        r = requests.get("https://api.genderize.io", params={"name": primeiro.lower()}, timeout=3)
        if r.status_code == 200:
            data = r.json()
            genero = data.get("gender")
            prob = data.get("probability", 0)

            if genero == "female" and prob > 0.7:
                cache_sexo[primeiro] = "F"
                return "F"
            elif genero == "male" and prob > 0.7:
                cache_sexo[primeiro] = "M"
                return "M"
    except:
        pass

    cache_sexo[primeiro] = ""
    return ""

def mapear_etnia(cor):
    cor = remover_acentos(cor.upper())

    if "BRANC" in cor: return "1"
    if "PRET" in cor: return "2"
    if "PARD" in cor: return "3"
    if "AMAREL" in cor: return "4"
    if "INDIGENA" in cor: return "5"
    if "NAO" in cor: return "6"

    return ""

def processar_pdf(caminho_pdf):
    texto = ""

    with pdfplumber.open(caminho_pdf) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                texto += t + "\n"

    alunos = []

    blocos = re.split(r"ALUNO:\s+", texto)

    for bloco in blocos[1:]:
    try:
        texto = limpar_texto(bloco)

        texto = texto.replace(" CPF:", "|CPF:")
        texto = texto.replace(" DATA:", "|DATA:")
        texto = texto.replace(" BAIRRO:", "|BAIRRO:")
        texto = texto.replace(" MÃE:", "|MAE:")
        texto = texto.replace(" PAI:", "|PAI:")
        texto = texto.replace(" COR:", "|COR:")
        texto = texto.replace(" CIDADE:", "|CIDADE:")
        texto = texto.replace(" EMAIL:", "|EMAIL:")

        partes = texto.split("|")

        dados = {}
        dados["nome"] = partes[0].strip()

        for p in partes[1:]:
            if "CPF:" in p:
                dados["cpf"] = limpar_cpf(p.replace("CPF:", ""))
            elif "DATA:" in p:
                dados["nascimento"] = p.replace("DATA:", "").strip()
            elif "BAIRRO:" in p:
                dados["bairro"] = p.replace("BAIRRO:", "").strip()
            elif "MAE:" in p:
                dados["mae_nome"] = p.replace("MAE:", "").strip()
            elif "PAI:" in p:
                dados["pai_nome"] = p.replace("PAI:", "").strip()
            elif "COR:" in p:
                dados["etnia"] = mapear_etnia(p.replace("COR:", ""))
            elif "CIDADE:" in p:
                dados["cidade"] = p.replace("CIDADE:", "").strip()

        endereco_match = re.search(r"DATA:.*?- (.*?)(EMAIL|BAIRRO|$)", bloco)
        endereco = endereco_match.group(1).strip() if endereco_match else ""

        cidade = ""
        logradouro = ""
        numero = ""

        if endereco:
            partes_end = endereco.split(" ", 1)
            if len(partes_end) > 1:
                cidade = partes_end[0]
                logradouro = partes_end[1]

            num = re.search(r"(\d+|S/N)$", logradouro)
            if num:
                numero = num.group(1)
                logradouro = logradouro.replace(numero, "").strip()

        # 🔥 SEXO AUTOMÁTICO
        sexo = inferir_sexo(dados.get("nome", ""))

        alunos.append({
            "nome": dados.get("nome", ""),
            "cpf": dados.get("cpf", ""),
            "nascimento": dados.get("nascimento", ""),
            "sexo": sexo,
            "logradouro": logradouro,
            "numero": numero,
            "bairro": dados.get("bairro", ""),
            "cidade": cidade or dados.get("cidade", ""),
            "estado": "CE",
            "etnia": dados.get("etnia", ""),
            "mae_nome": dados.get("mae_nome", ""),
            "pai_nome": dados.get("pai_nome", ""),
            "telefone": ""
        })

    except Exception as e:
        print("Erro:", e)
        continue

    df = pd.DataFrame(alunos)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv
