# Large Language Models para Recuperação da Informação em Acervos Históricos Digitalizados

Este repositório contém os **códigos utilizados** na pesquisa de dissertação intitulada **Large Language Models para recuperação da informação em acervos históricos digitalizados**, desenvolvida por **Daiane Campos Procópio**, no âmbito do Programa de Pós-Graduação em Gestão e Organização do Conhecimento da Escola de Ciência da Informação da UFMG.

A pesquisa investigou o uso de Large Language Models (LLMs) para identificar e recuperar informações de teses digitalizadas, incluindo documentos que não possuem o texto reconhecível por máquina.

---

## Estrutura do Código

O código principal realiza as seguintes etapas:

1. **Leitura e pré-processamento dos arquivos PDF**
   - Conversão de páginas do PDF em imagem com `pdf2image`.
   - Aplicação de Reconhecimento Óptico de Caracteres (OCR) com `pytesseract` para extrair o texto das imagens.

2. **Perguntas sobre o conteúdo dos documentos**
   - Cinco perguntas são feitas sobre cada tese, abordando título, autor, resumo, objetivo, metodologia e conclusões.

3. **Interação com os LLMs**
   - O texto extraído é enviado ao modelo definido (`llama3.2`, `qwen2.5`, ou `mistral`) por meio da API **Ollama**, utilizando *prompts* em português.

4. **Limpeza e pós-processamento das respostas**
   - O texto é filtrado e padronizado, eliminando ruídos e expressões irrelevantes, com substituição de termos técnicos comuns.

5. **Exportação dos resultados**
   - Os resultados são salvos em formato `.csv` no diretório definido, contendo as respostas organizadas por tese.

---

## Bibliotecas Utilizadas

| Biblioteca | Função principal |
|-------------|------------------|
| `os` | Manipulação de diretórios e arquivos |
| `fitz` (PyMuPDF) | Leitura e manipulação de PDFs |
| `pytesseract` | Reconhecimento Óptico de Caracteres (OCR) |
| `pdf2image` | Conversão de PDF para imagens |
| `pandas` | Estruturação e exportação dos resultados |
| `ollama` | Interface com os LLMs |
| `re` | Expressões regulares para limpeza de texto |

---

## Como executar

Instale as dependências:

   *pip install pymupdf pytesseract pdf2image pandas ollama*

Certifique-se de que o Tesseract OCR esteja instalado e configurado no PATH do sistema.

Ajuste os caminhos das pastas conforme sua estrutura local.

Execute o script.

Verifique o arquivo .csv gerado no diretório de resultados.
