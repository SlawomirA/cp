import base64
import io
import json
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from keybert import KeyBERT
from pdf2image import convert_from_path
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy.future import select
import subprocess
import requests
import os

from pytesseract import pytesseract
from fastapi.responses import StreamingResponse
from starlette.responses import PlainTextResponse

import spacy
import language_tool_python

from src.database import get_db
from src.engine import Engine
from src.http_models import DetailedResponse
from src.models import File_Model

router = APIRouter()

pytesseract.tesseract_cmd = r'D:\Programowanie\TesseractOCR\tesseract.exe' # r'C:\Program Files\Tesseract-OCR\tesseract.exe' # r'D:\Programowanie\TesseractOCR\tesseract.exe'
nlp = spacy.load("pl_core_news_sm")
tool = language_tool_python.LanguageTool('pl')
model = KeyBERT('distilbert-base-nli-mean-tokens')

class PDFUrlResponse(BaseModel):
    pdf_urls: List[str]


@router.get("/download-pdf/", tags=["etap1"])
async def download_pdf(url: str):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to download the PDF.")

        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        downloads_path = Path.home() / "Downloads"
        downloads_path.mkdir(parents=True, exist_ok=True)

        file_path = downloads_path / filename

        with open(file_path, 'wb') as f:
            f.write(response.content)

        return {
            "message": "PDF downloaded successfully",
            "file_path": str(file_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download-pdf-return/", tags=["etap1"])
async def download_pdf(url: str):
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to download the PDF.")

        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)

        # pdf_buffer = io.BytesIO(response.content)
        pdf_buffer = base64.b64encode(response.content).decode('utf-8')
        return {"pdf": pdf_buffer}
        # return StreamingResponse(
        #     pdf_buffer,
        #     media_type="application/pdf",
        #     headers={
        #         "Content-Disposition": f"attachment; filename={filename}"
        #     }
        # )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scrape-pdfs/", tags=["etap1"])
async def scrape_pdfs(start_url: str):
    print("Start URL:", start_url)
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
            print("PDF Links:", pdf_links)
        return {"pdf_links": json.loads(pdf_links)}

    return {"message": "Scraping completed but no PDF links found."}


@router.post("/ocr-pdf", tags=["etap2"], response_class=PlainTextResponse)
async def upload_pdf(file: UploadFile = File(...)):
    print("upload pdf\n", file)
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    try:
        images = convert_from_path(temp_file_path)  #PDF to images

        extracted_text = ""  #OCR on each image, collect the text
        for image in images:
            text = pytesseract.image_to_string(image, lang='pol')
            extracted_text += text + "\n"
        print(extracted_text)
        return extracted_text.strip()
    finally:
        os.remove(temp_file_path)


class CorrectTextInput(BaseModel):
    input_text: str


@router.post("/correct-text", tags=['etap2'])
async def correct_text(correct_text: CorrectTextInput):
    try:
        original_text = correct_text.input_text
        corrected_text = str(tool.correct(original_text))

        sanitized_text = original_text.replace("\r\n", "\n").replace("\r", "\n")

        return {
            "original_text": sanitized_text,
            "corrected_text": corrected_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the text: {str(e)}")


class AskAdviceInput(BaseModel):
    question: str
    fileId: Optional[int] = None

@router.post("/ask-for-advice", tags=['etap3'])
async def ask_for_advice(
    askadvice_input: AskAdviceInput = Depends(),
    input_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        engine = Engine()
        if askadvice_input.fileId:
            file = db.execute(select(File_Model).filter_by(FI_ID=askadvice_input.fileId)).scalars().first()
            input_text = file.Content
        elif input_file:
            if not input_file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

            temp_file_path = f"temp_{input_file.filename}"
            with open(temp_file_path, "wb") as temp_file:
                content = await input_file.read()
                temp_file.write(content)

            try:
                images = convert_from_path(temp_file_path)
                extracted_text = ""
                for image in images:
                    text = pytesseract.image_to_string(image, lang='pol')
                    extracted_text += text + "\n"

                input_text = extracted_text.strip()

                new_file = File_Model(
                    Name=input_file.filename,
                    Url='Missing url',
                    Content=input_text
                )
                db.add(new_file)
                db.commit()
            finally:
                os.remove(temp_file_path)
        else:
            input_text = askadvice_input.input_text

        result = engine.connection(input_text, askadvice_input.question)

        return {
            "prompt": engine.create_prompt(input_text, askadvice_input.question),
            "answer": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing the text: {str(e)}")


class ExtractKeywordsText(BaseModel):
    request: str


@router.post("/extract-keywords", tags=['etap3'])
async def extract_keywords(keywordsText: ExtractKeywordsText):
    try:
        keywords = model.extract_keywords(
            keywordsText.request,
            keyphrase_ngram_range=(1, 2),
            stop_words=None,
            top_n=7
        )

        return {
            "keywords": [{"keyword": kw[0]} for kw in keywords]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting keywords: {str(e)}")


@router.post("/load-pdf-data", tags=["etap2"])
async def load_pdf_data(url: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    try:
        images = convert_from_path(temp_file_path)  #PDF to images

        extracted_text = ""
        for image in images:
            text = pytesseract.image_to_string(image, lang='pol')
            extracted_text += text + "\n"
        corrected_text = str(tool.correct(extracted_text))
        try:

            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            new_file = File_Model(
                Name=filename,
                Url=url,
                Content=extracted_text,
                Corretted_Content=corrected_text
            )
            db.add(new_file)
            db.commit()
            db.refresh(new_file)  # Refresh to get the ID and other defaults

            keywords = model.extract_keywords(
                new_file.Corretted_Content,
                keyphrase_ngram_range=(1, 2),
                stop_words=None,
                top_n=7
            )

            response_data = {
                "FI_ID": new_file.FI_ID,
                "Content": new_file.Content,
                "Corrected_Content": new_file.Corretted_Content,
                "Keywords": [kw[0] for kw in keywords]
            }

            return DetailedResponse(code=201, message="File successfully saved", data=response_data)

        except Exception as e:
            db.rollback()
            print(f"Error occurred while saving file: {e}")
            raise HTTPException(status_code=500, detail="Error occurred while saving the file")
    finally:
        os.remove(temp_file_path)
