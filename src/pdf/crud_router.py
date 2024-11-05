from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from keybert import KeyBERT
from pdf2image import convert_from_path
from pydantic import BaseModel, create_model
import subprocess
import requests
import os

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from sqlalchemy.orm import Session

from src.database import get_db
from pytesseract import pytesseract
from starlette.responses import PlainTextResponse

from src.database import SessionLocal
from src.http_models import DetailedResponse
from src.models import File_Keyword, File_Model, LLM_Message
from src.request_models import SaveFileUpload, SaveKeywordsUpload, SaveChatUpload
from src.response_models import FileModelResponse, LLMMessageResponse

router = APIRouter()





@router.post("/save-file", tags=["crud_etap1"], response_model=DetailedResponse)
async def save_file(file_upload: SaveFileUpload, db: Session = Depends(get_db)) -> DetailedResponse:

    try:
        response_data = await save_file_to_database(db, file_upload)

        return DetailedResponse(code=201, message="File successfully saved", data=response_data)

    except Exception as e:
        db.rollback()
        print(f"Error occurred while saving file: {e}")
        raise HTTPException(status_code=500, detail="Error occurred while saving the file")


async def save_file_to_database(db, file_upload):
    new_file = File_Model(
        Name=file_upload.name,
        Url=file_upload.url,
        Content=file_upload.content
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)  # Refresh to get the ID and other defaults
    response_data = {
        "FI_ID": new_file.FI_ID,
        "Name": new_file.Name,
        "Url": new_file.Url,
        "Content": new_file.Content,
        "Corretted_Content": new_file.Corretted_Content,  # None initially
    }
    return response_data


@router.get("/download-corrected-txt/", tags=["etap2"])
async def download_corrected_txt(fileId: int, db: Session = Depends(get_db)):
    try:
        # Retrieve file record from database
        file_record = db.query(File_Model).filter(File_Model.FI_ID == fileId).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        filename = f"{file_record.Name}_corrected.txt" if file_record.Name else f"file_{fileId}_corrected.txt"
        file_path = os.path.join("downloads", filename)

        os.makedirs("downloads", exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_record.Corretted_Content)

        return FileResponse(path=file_path, filename=filename, media_type='text/plain')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-keywords", tags=["crud_etap3"], response_model=DetailedResponse)
async def save_keywords(
        saveKeywordsUpload: SaveKeywordsUpload,
        db: Session = Depends(get_db)
) -> DetailedResponse:
    file_exists = db.execute(
        select(File_Model).filter_by(FI_ID=saveKeywordsUpload.fileId)
    ).scalars().first()
    if not file_exists:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        db.query(File_Keyword).filter_by(FI_ID=saveKeywordsUpload.fileId).delete(synchronize_session='fetch')

        new_keywords = []
        for keyword in saveKeywordsUpload.keywords:
            new_keyword = File_Keyword(FI_ID=saveKeywordsUpload.fileId, Keyword=keyword)
            new_keywords.append(new_keyword)
            db.add(new_keyword)

        db.commit()

        serialized_keywords = [KeywordResponse.from_orm(keyword) for keyword in new_keywords]

        return DetailedResponse(code=201, message="Correctly saved", data=serialized_keywords)

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return DetailedResponse(code=500, message="Error", error=str(e))



@router.post("/save-chat-history", tags=["crud_etap3"], response_model=DetailedResponse)
# async def save_chat_history(prompt: str, answer: str, file_id: Optional[int] = None,  db: Session = Depends(get_db)) -> DetailedResponse:
async def save_chat_history(saveChatUpload: SaveChatUpload,  db: Session = Depends(get_db)) -> DetailedResponse:
    if saveChatUpload.file_id is not None:
        file_exists = db.execute(select(File_Model).filter_by(FI_ID=saveChatUpload.file_id)).scalars().first()
        if not file_exists:
            raise HTTPException(status_code=404, detail="File not found")

    try:
        llm_message = LLM_Message(Prompt=saveChatUpload.prompt, Answer=saveChatUpload.answer, FI_ID=saveChatUpload.file_id)
        db.add(llm_message)
        db.commit()
        return DetailedResponse(code=201, message="Correctly saved", data=LLMMessageResponse.from_orm(llm_message))
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return DetailedResponse(code=500, message="Error", error=str(e))


class SaveCorrectedTextUpload(BaseModel):
    fileId: int
    corrected_text: str


@router.patch("/save-corrected-text", tags=["crud_etap2"], response_model=DetailedResponse)
async def save_corrected_text(saveCorrectedTextUpload: SaveCorrectedTextUpload, db: Session = Depends(get_db)) -> DetailedResponse:
    file_instance  =  db.execute(select(File_Model).filter_by(FI_ID=saveCorrectedTextUpload.fileId)).scalars().first()
    if not file_instance :
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_instance.Corretted_Content = saveCorrectedTextUpload.corrected_text
        db.commit()

        return True
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return False