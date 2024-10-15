from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File
from keybert import KeyBERT
from pdf2image import convert_from_path
from pydantic import BaseModel
import subprocess
import requests
import os

from pytesseract import pytesseract
from starlette.responses import PlainTextResponse

import spacy
import language_tool_python

from src.engine import Engine

router = APIRouter()

pytesseract.tesseract_cmd = r'D:\Programowanie\TesseractOCR\tesseract.exe'
nlp = spacy.load("pl_core_news_sm")
tool = language_tool_python.LanguageTool('pl')
model = KeyBERT('distilbert-base-nli-mean-tokens')

class PDFUrlResponse(BaseModel):
    pdf_urls: List[str]


@router.get("/download-pdf/", tags=["etap1"])
async def download_pdf(url: str, filename: str):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to download the PDF.")

        file_path = os.path.join(os.getcwd(), filename)

        with open(file_path, 'wb') as f:
            f.write(response.content)

        return {"message": "PDF downloaded successfully", "file_path": file_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scrape-pdfs/", tags=["etap1"])
async def scrape_pdfs(start_url: str):
    project_dir = os.path.join(os.getcwd(), 'src', 'pdf_scraper')

    process = subprocess.Popen(
        ['scrapy', 'crawl', 'pdf_spider', '-a', f'start_url={start_url}'],
        cwd=project_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    if stderr and 'Crawled (200)' not in stderr.decode().strip():
        print(stderr.decode())
        raise HTTPException(status_code=500, detail=stderr.decode())

    pdf_links_path = os.path.join(project_dir, 'pdf_links.json')
    if os.path.exists(pdf_links_path):
        with open(pdf_links_path, 'r') as f:
            pdf_links = f.read()
        return {"pdf_links": pdf_links}

    return {"message": "Scraping completed but no PDF links found."}


@router.post("/ocr-pdf", tags=["etap2"], response_class=PlainTextResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    # Save the uploaded PDF to a tmp file
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    try:
        images = convert_from_path(temp_file_path)  # PDF to images

        extracted_text = ""  # OCR on each image, collect the text
        for image in images:
            text = pytesseract.image_to_string(image, lang='pol')
            extracted_text += text + "\n"

        return extracted_text.strip()
    finally:
        os.remove(temp_file_path)


@router.post("/correct-text", tags=['etap2'])
async def correct_text(input_text: str):
    try:
        original_text = input_text
        corrected_text = str(tool.correct(original_text))

        sanitized_text = original_text.replace("\r\n", "\n").replace("\r", "\n")

        return {
            "original_text": sanitized_text,
            "corrected_text": corrected_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the text: {str(e)}")


@router.post("/ask-for-advice", tags=['etap3'])
async def ask_for_advice(input_text: str, question: str):
    try:
        engine = Engine()
        result = engine.connection(input_text, question)

        return {
            "prompt": engine.create_prompt(input_text, question),
            "answer": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the text: {str(e)}")


@router.post("/extract-keywords")
async def extract_keywords(request: str, number_of_cases: int):
    try:
        keywords = model.extract_keywords(
            request,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=number_of_cases
        )

        return {
            "keywords": [{"keyword": kw[0], "score": kw[1]} for kw in keywords]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting keywords: {str(e)}")


# @router.post("/upload_pdf/")
# async def upload_pdf(file: UploadFile = File(...)):
#     db = SessionLocal()
#     pdf_data = await file.read()
#     db_pdf = PDFFile(file_data=pdf_data)
#     db.add(db_pdf)
#     db.commit()
#     db.refresh(db_pdf)
#     return {"file_id": db_pdf.id}
