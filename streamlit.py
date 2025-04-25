import os
import fitz
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import ollama
import streamlit as st
import re

# ------------------ CONFIGURAÇÕES ------------------
MODELO = "llama3:8b"
PASTA_SAIDA = "respostas"
os.makedirs(PASTA_SAIDA, exist_ok=True)

# ------------------ FUNÇÕES ------------------
def extrair_texto_paginas(pdf_path):
    imagens = convert_from_path(pdf_path)
    textos = [pytesseract.image_to_string(img, lang='por') for img in imagens]
    return textos

def gerar_prompt(pergunta, texto):
    return f"""
Leia o texto da tese abaixo e responda APENAS em português, sem explicar ou repetir a pergunta.

{texto}

Responda com frases curtas, diretas, sem justificativas. Evite dizer que não encontrou conteúdo se houver informação parcial.

{pergunta}
"""

def chamar_ollama(modelo, prompt):
    try:
        resposta = ollama.chat(model=modelo, messages=[{"role": "user", "content": prompt}])
        return resposta['message']['content'].strip()
    except Exception as e:
        return f"[ERRO] {str(e)}"

def limpar_resposta(texto):
    if pd.isna(texto) or not texto.strip():
        return "Vazio"
    texto = texto.strip()
    if texto.upper().startswith("AAA") or re.fullmatch(r"\d{1,2}", texto):
        return "Texto com ruído OCR - não interpretado."
    return texto

def processar_tese(pdf_path, perguntas, faixas_paginas):
    try:
        texto_paginas = extrair_texto_paginas(pdf_path)
        total_paginas = len(texto_paginas)
        respostas = []

        for i, pergunta in enumerate(perguntas):
            faixas = faixas_paginas[i]
            if faixas == "ultimas_40":
                faixas = list(range(max(0, total_paginas - 40), total_paginas))
            trecho = "\n".join([texto_paginas[p] for p in faixas if p < total_paginas])
            prompt = gerar_prompt(pergunta, trecho)
            resposta = chamar_ollama(MODELO, prompt)
            respostas.append(limpar_resposta(resposta))
        return respostas
    except Exception as e:
        return [f"[ERRO OCR] {str(e)}"] * len(perguntas)

def salvar_csv(dados, nome_saida):
    df = pd.DataFrame(dados)
    caminho = os.path.join(PASTA_SAIDA, nome_saida)
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return caminho

# ------------------ STREAMLIT ------------------
st.title("🔍 Analisador de Teses com LLaMA 3.2")
st.write("Extração automatizada de título, resumo, objetivos, metodologia e conclusão")

arquivos = st.file_uploader("Envie os arquivos PDF das teses", type="pdf", accept_multiple_files=True)

if arquivos:
    perguntas = [
        "1. Qual é o título da tese e o nome do autor(a)?",
        "2. Resuma o conteúdo principal da tese em até 3 frases.",
        "3. Qual é o objetivo principal desta tese?",
        "4. Quais foram os principais passos metodológicos utilizados na pesquisa?",
        "5. Quais são as principais conclusões ou resultados obtidos com a pesquisa?"
    ]

    faixas_paginas = [
        [0],
        list(range(5, 25)),
        list(range(10, 30)),
        list(range(15, 35)),
        "ultimas_40"
    ]

    resultados = []
    for arquivo in arquivos:
        nome = arquivo.name
        st.write(f"📄 Processando: {nome}")
        caminho_temp = os.path.join("temp_", nome)
        with open(caminho_temp, "wb") as f:
            f.write(arquivo.read())
        respostas = processar_tese(caminho_temp, perguntas, faixas_paginas)
        os.remove(caminho_temp)
        resultados.append({
            "Arquivo": nome,
            "Título e Autor": respostas[0],
            "Resumo": respostas[1],
            "Objetivo": respostas[2],
            "Metodologia": respostas[3],
            "Conclusões": respostas[4],
        })

    caminho_saida = salvar_csv(resultados, "respostas_llama3_streamlit.csv")
    st.success("Análise concluída!")
    st.download_button("📥 Baixar respostas em CSV", caminho_saida, file_name="respostas_llama3.csv")
