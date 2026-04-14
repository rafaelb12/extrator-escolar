import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import base64
import unicodedata
import requests

st.set_page_config(page_title="Extrator de Alunos", layout="wide")

st.title("📄 Extrator de Alunos (PDF → CSV)")
st.write("Envie vários PDFs e gere uma única planilha automaticamente.")

# Upload
arquivos = st.file_uploader("Selecione os PDFs", type="pdf", accept_multiple_files=True)

# Funções básicas (resumo do seu código)
def limpar(texto):
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()

def extrair_info(padrao, texto):
    m = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
    return limpar(m.group(1)) if m else ""

# Processamento
if st.button("🚀 Processar PDFs"):
    if not arquivos:
        st.error("Envie pelo menos um PDF")
    else:
        todos = []
        progresso = st.progress(0)

        for i, arquivo in enumerate(arquivos):
            texto = ""

            with pdfplumber.open(io.BytesIO(arquivo.read())) as pdf:
                for pagina in pdf.pages:
                    texto += pagina.extract_text() or ""

            blocos = re.split(r"ALUNO:", texto)

            for bloco in blocos[1:]:
                nome = extrair_info(r"^(.*?)(CPF|DATA)", bloco)
                nascimento = extrair_info(r"(\d{2}/\d{2}/\d{4})", bloco)

                if nome:
                    todos.append({
                        "nome": nome,
                        "nascimento": nascimento
                    })

            progresso.progress((i + 1) / len(arquivos))

        if todos:
            df = pd.DataFrame(todos)

            st.success(f"✅ {len(df)} alunos extraídos!")
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8-sig")

            st.download_button(
                "📥 Baixar CSV",
                data=csv,
                file_name="alunos.csv",
                mime="text/csv"
            )
        else:
            st.warning("Nenhum aluno encontrado")
