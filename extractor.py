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
            linha = limpar_texto(bloco)

            # NOME
            nome = re.search(r"^(.*?)\s+CPF:", linha)
            nome = nome.group(1) if nome else ""

            # CPF
            cpf = re.search(r"CPF:\s*([\d\.\-]+)", linha)
            cpf = limpar_cpf(cpf.group(1)) if cpf else ""

            # DATA
            nascimento = re.search(r"DATA:\s*([0-9/]+)", linha)
            nascimento = nascimento.group(1) if nascimento else ""

            # ENDEREÇO
            endereco = re.search(r"DATA:.*?- (.*?)(EMAIL|BAIRRO|$)", linha)
            endereco = endereco.group(1).strip() if endereco else ""

            cidade = ""
            logradouro = ""
            numero = ""

            if endereco:
                partes = endereco.split(" ", 1)
                if len(partes) > 1:
                    cidade = partes[0]
                    logradouro = partes[1]

                num = re.search(r"(\d+|S/N)$", logradouro)
                if num:
                    numero = num.group(1)
                    logradouro = logradouro.replace(numero, "").strip()

            # BAIRRO
            bairro = re.search(r"BAIRRO:\s*(.*?)(ALUNO|$)", linha)
            bairro = bairro.group(1).strip() if bairro else ""

            # MÃE
            mae = re.search(r"M[ÃA]E:\s*(.*?)(PAI|CPF|$)", linha)
            mae = mae.group(1).strip() if mae else ""

            # PAI
            pai = re.search(r"PAI:\s*(.*?)(RG|COR|$)", linha)
            pai = pai.group(1).strip() if pai else ""

            # ETNIA
            cor = re.search(r"COR:\s*(.*?)(CIDADE|$)", linha)
            etnia = mapear_etnia(cor.group(1)) if cor else ""

            # TELEFONE
            telefone = re.search(r"(\(?\d{2}\)?\s?\d{4,5}-?\d{4})", linha)
            telefone = telefone.group(1) if telefone else ""

            # SEXO AUTOMÁTICO
            sexo = inferir_sexo(nome)

            alunos.append({
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
                "pai_nome": pai,
                "telefone": telefone
            })

        except:
            continue

    df = pd.DataFrame(alunos)

    caminho_csv = caminho_pdf.replace(".pdf", ".csv")
    df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")

    return caminho_csv
