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
modelo_ollama = "mistral"

# Perguntas e mapeamento de páginas
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

# Função para aplicar OCR ao PDF por página
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

# Função para limpar e classificar respostas
def limpar_resposta(texto):
    if pd.isna(texto):
        return texto, "Comentário"
    texto = str(texto).strip()
    if texto.upper().startswith("AAA") or re.fullmatch(r"[A-Z ]{5,}", texto):
        return "Texto com ruído OCR - não interpretado.", "Comentário"
    if re.fullmatch(r"\d{1,2}", texto):
        return "Texto com ruído OCR - não interpretado.", "Comentário"

    # Remoção de frases de raciocínio e marcação
    classificacao = "Resposta Válida"
    if any(palavra in texto.lower() for palavra in ["parece", "aparentemente", "provavelmente", "pode ser"]):
        classificacao = "Comentário"

    texto = re.sub(r"(?i)^(okay|primeiro|vou tentar|preciso|então|bem|let me).*?(\.|\n)", '', texto)
    texto = re.sub(r"<think>.*?(?=\n|$)", "", texto, flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r'^.*?(resposta|answer):\s*', '', texto, flags=re.IGNORECASE)

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
        classificacao = "Comentário"

    return texto.strip(), classificacao

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
    classificacoes = []

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
A seguir está o conteúdo de uma tese. Leia atentamente e responda apenas com a informação solicitada. NÃO explique seu raciocínio. NÃO comente se parece ou provavelmente. Responda apenas em português, com frases objetivas e diretas:

{texto_segmento}

{pergunta}
""".strip()

        resposta = chamar_ollama(modelo_ollama, prompt)
        resposta_limpa, classificacao = limpar_resposta(resposta)
        respostas.append(resposta_limpa)
        classificacoes.append(classificacao)

    dados = {
        "Arquivo": arquivo,
        "Título e Autor": respostas[0] if len(respostas) > 0 else "",
        "Resumo": respostas[1] if len(respostas) > 1 else "",
        "Objetivo": respostas[2] if len(respostas) > 2 else "",
        "Metodologia": respostas[3] if len(respostas) > 3 else "",
        "Conclusões": respostas[4] if len(respostas) > 4 else "",
        "Classificação Título e Autor": classificacoes[0] if len(classificacoes) > 0 else "",
        "Classificação Resumo": classificacoes[1] if len(classificacoes) > 1 else "",
        "Classificação Objetivo": classificacoes[2] if len(classificacoes) > 2 else "",
        "Classificação Metodologia": classificacoes[3] if len(classificacoes) > 3 else "",
        "Classificação Conclusões": classificacoes[4] if len(classificacoes) > 4 else ""
    }
    resultados.append(dados)

# Salva resultados
df = pd.DataFrame(resultados)
caminho_csv = os.path.join(pasta_resultados, "respostas_mistral.csv")
df.to_csv(caminho_csv, index=False, encoding="utf-8-sig")
print(f"\n Resultados salvos em: {caminho_csv}")