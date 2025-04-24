import os
import sys
import fitz
import pandas as pd
import pytesseract
import requests
from pdf2image import convert_from_path

# === Evita erro de encoding no terminal do Windows
sys.stdout.reconfigure(encoding='utf-8')

# === CONFIGURAÇÕES ===
diretorio = r"C:\\Users\\proco\\OneDrive\\Área de Trabalho\\Qualificação\\Teses\\1_CienciasExataseDaTerra"
saida_csv = r"C:\\Users\\proco\\OneDrive\\Área de Trabalho\\Qualificação\\Codigos\\Respostas\\respostas_mistral.csv"
poppler_path = r"C:\\poppler\\Library\\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
modelo_ollama = "mistral"

# === EXTRAÇÃO DE TEXTO COM OCR (TODAS AS PÁGINAS) ===
def extrair_texto(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        texto = ""
        for pagina in doc:
            texto += pagina.get_text("text") + "\n"
    except:
        texto = ""

    if not texto.strip():
        print(f"[OCR] '{os.path.basename(pdf_path)}' parece ser imagem. Aplicando OCR...")
        try:
            imagens = convert_from_path(pdf_path, dpi=150, poppler_path=poppler_path)
            texto = ""
            for img in imagens:
                texto += pytesseract.image_to_string(img, lang="por")
        except Exception as e:
            print(f"[ERRO] Falha no OCR: {e}")
            return ""

    return texto.strip()[:18000]  # corta se exceder ~8000 tokens (~20k caracteres)

# === MONTA O PROMPT PARA OLLAMA ===
def montar_prompt(texto):
    return (
        "Com base no texto da tese abaixo, responda diretamente (sem explicações) separando as respostas com ' ||| ' :\n"
        "1. Qual é o título da tese e o nome do autor(a)?\n"
        "2. Resuma o conteúdo principal da tese em até 3 frases.\n"
        "3. Qual é o objetivo principal desta tese?\n"
        "4. Descreva brevemente a metodologia aplicada na tese.\n"
        "5. Quais são as principais conclusões ou resultados apresentados na tese?\n\n"
        f"TEXTO DA TESE:\n{texto}\n\n"
        "Formato da resposta: Resposta 1 ||| Resposta 2 ||| Resposta 3 ||| Resposta 4 ||| Resposta 5"
    )

# === ENVIA AO OLLAMA COM TRATAMENTO DE ERROS ===
def chamar_ollama(prompt):
    try:
        resposta = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": modelo_ollama, "prompt": prompt, "stream": False}
        )
        dados = resposta.json()
        if "response" in dados:
            bruto = dados["response"].strip()
            linhas = bruto.splitlines()
            limpas = [l for l in linhas if not l.strip().startswith("<")]
            return " ".join(limpas).strip()
        else:
            print("[ERRO] Resposta inesperada do modelo:", dados)
            return "Não foi possível gerar resposta"
    except Exception as e:
        print(f"[ERRO] Falha na chamada ao Ollama: {e}")
        return "Erro na chamada ao modelo"

# === PROCESSAMENTO COMPLETO ===
resultados = []
todos_arquivos = [f for f in os.listdir(diretorio) if f.lower().endswith(".pdf")]
total = len(todos_arquivos)
contador = 0

for arquivo in todos_arquivos:
    contador += 1
    print(f"\n[{contador}/{total}] Processando: {arquivo}")
    caminho_pdf = os.path.join(diretorio, arquivo)
    texto = extrair_texto(caminho_pdf)

    if not texto:
        print(f"[SKIP] Sem conteúdo extraído de '{arquivo}'")
        continue

    prompt = montar_prompt(texto)
    resposta = chamar_ollama(prompt)
    respostas = [r.strip() for r in resposta.split("|||")]

    dados = {
        "Arquivo": arquivo,
        "Título e Autor": respostas[0] if len(respostas) > 0 else "Não encontrado",
        "Resumo": respostas[1] if len(respostas) > 1 else "Não encontrado",
        "Objetivo": respostas[2] if len(respostas) > 2 else "Não encontrado",
        "Metodologia": respostas[3] if len(respostas) > 3 else "Não encontrado",
        "Conclusões": respostas[4] if len(respostas) > 4 else "Não encontrado"
    }

    resultados.append(dados)
    pd.DataFrame(resultados).to_csv(saida_csv, index=False, encoding="utf-8-sig")
    print(f"[✔] '{arquivo}' processado.")

print(f"\n[✅ FIM] Total de arquivos processados: {len(resultados)}")
print(f"[📁] Resultados salvos em: {saida_csv}")
