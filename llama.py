# Bibliotecas
import os
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import ollama
import re

# Diretórios
pasta_teses = r"C:\\Users\\proco\\OneDrive\\Área de Trabalho\\Qualificação\\Teses\\1_CienciasExataseDaTerra"
pasta_resultados = r"C:\\Users\\proco\\OneDrive\\Área de Trabalho\\Qualificação\\Codigos\\Respostas"

# Modelo Ollama
modelo_ollama = "llama3.2"

# Perguntas e mapeamento de páginas - Os modelos não rodam todas as páginas por limitação de tokens, então foi necessário indicar páginas para a pesquisa das respostas.
perguntas = [
    "1. Qual é o título da tese e o nome do autor(a)?",
    "2. Resuma o conteúdo principal da tese em até 3 frases.",
    "3. Qual é o objetivo principal desta tese?",
    "4. Descreva brevemente a metodologia aplicada na tese.",
    "5. Quais são as principais conclusões ou resultados apresentados na tese?"
]

mapeamento_paginas = [
    [0],
    list(range(5, 20)),
    list(range(8, 28)),
    list(range(10, 30)),
    "ultimas_50"
]

# Função para aplicar OCR ao PDF por página - Identificação dos caracteres
def extrair_texto_paginas(pdf_path):
    imagens = convert_from_path(pdf_path)
    textos = []
    for img in imagens:
        texto = pytesseract.image_to_string(img, lang='por')
        textos.append(texto)
    return textos

# Função para chamada ao Ollama
def chamar_ollama(modelo, prompt):
    try:
        resposta = ollama.chat(model=modelo, messages=[{"role": "user", "content": prompt}])
        return resposta['message']['content'].strip()
    except Exception as e:
        return f"[ERRO OLLAMA] {str(e)}"

# Função para limpar e suavizar respostas
def limpar_resposta(texto):
    if pd.isna(texto):
        return texto
    texto = str(texto).strip()
    if texto.upper().startswith("AAA") or re.fullmatch(r"[A-Z ]{5,}", texto):
        return "Texto com ruído OCR - não interpretado."
    if re.fullmatch(r"\d{1,2}", texto):
        return "Texto com ruído OCR - não interpretado."

    padroes = [
        r'^O título.*?:\s*', r'^Aqui está.*?:\s*', r'^A metodologia.*?:\s*',
        r'^Based on the provided.*?:\s*', r'^Based on the text.*?:\s*', r'^Resumo[:\s]*',
        r'^Análise.*?:\s*', r'^Objetivo[:\s]*'
    ]
    for padrao in padroes:
        texto = re.sub(padrao, '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'\n+', ' ', texto)
    texto = re.sub(r'\s{2,}', ' ', texto)

    substituicoes = {
        "FFT": "Transformada Rápida de Fourier",
        "Hamiltonian": "modelo Hamiltoniano",
        "paramagnetic": "paramagnético",
        "hyperfine": "hiperfino",
        "No.": "Conteúdo não identificado claramente no trecho analisado"
    }
    for termo, traducao in substituicoes.items():
        texto = texto.replace(termo, traducao)

    if "não apresenta" in texto.lower() and len(texto.split()) < 10:
        texto = "Conteúdo não identificado claramente no trecho analisado."

    return texto.strip()

# Inicializa resultados
resultados = []

# Processa os arquivos PDF
arquivos = [arq for arq in os.listdir(pasta_teses) if arq.endswith(".pdf")]
for i, arquivo in enumerate(arquivos, 1):
    print(f"[{i}/{len(arquivos)}] Processando: {arquivo}")
    caminho_pdf = os.path.join(pasta_teses, arquivo)

    try:
        texto_paginas = extrair_texto_paginas(caminho_pdf)
    except Exception as e:
        print(f"[ERRO OCR] {arquivo}: {str(e)}")
        continue

    total_paginas = len(texto_paginas)
    respostas = []

    for idx, pergunta in enumerate(perguntas):
        paginas = mapeamento_paginas[idx]

        if isinstance(paginas, str) and paginas.startswith("ultimas_"):
            try:
                num = int(paginas.replace("ultimas_", ""))
                paginas = list(range(max(0, total_paginas - num), total_paginas))
            except ValueError:
                paginas = []

        texto_segmento = "\n".join([texto_paginas[p] for p in paginas if isinstance(p, int) and p < total_paginas])

        if not texto_segmento.strip():
            respostas.append("Texto não encontrado nas páginas indicadas.")
            continue

        prompt = f"""
A seguir está o conteúdo de uma tese. Leia atentamente e responda com objetividade e sem explicações. Não repita a pergunta. Responda apenas em português.

{texto_segmento}

Responda com frases curtas e diretas, evitando justificativas ou frases introdutórias. Evite dizer que não há conteúdo se houver informação parcial. Responda somente com a informação solicitada:

{pergunta}
""".strip()

        resposta = chamar_ollama(modelo_ollama, prompt)
        resposta_limpa = limpar_resposta(resposta)
        respostas.append(resposta_limpa)

    dados = {
        "Arquivo": arquivo,
        "Título e Autor": respostas[0] if len(respostas) > 0 else "",
        "Resumo": respostas[1] if len(respostas) > 1 else "",
        "Objetivo": respostas[2] if len(respostas) > 2 else "",
        "Metodologia": respostas[3] if len(respostas) > 3 else "",
        "Conclusões": respostas[4] if len(respostas) > 4 else "",
    }
    resultados.append(dados)

# Salva resultados
df = pd.DataFrame(resultados)
caminho_csv = os.path.join(pasta_resultados, "respostas_llama.csv")
df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
print(f"\n\ud83d\ude80 Resultados salvos em: {caminho_csv}")



