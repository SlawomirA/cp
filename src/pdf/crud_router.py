from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
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
from src.response_models import FileModelResponse, LLMMessageResponse

router = APIRouter()


@router.post("/save-file", tags=["crud_etap1"], response_model=DetailedResponse)
async def save_file(name: str, url: str, content: Optional[str] = None, db: Session = Depends(get_db)) -> DetailedResponse:
    try:
        new_file = File_Model(
            Name=name,
            Url=url,
            Content=content
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)  #Refresh to get the ID and other defaults

        response_data = {
            "FI_ID": new_file.FI_ID,
            "Name": new_file.Name,
            "Url": new_file.Url,
            "Content": new_file.Content,
            "Corretted_Content": new_file.Corretted_Content,  #None initially
        }

        return DetailedResponse(code=201, message="File successfully saved", data=response_data)

    except Exception as e:
        db.rollback()
        print(f"Error occurred while saving file: {e}")
        raise HTTPException(status_code=500, detail="Error occurred while saving the file")


@router.post("/save-keywords", tags=["crud_etap3"], response_model=DetailedResponse)
async def save_keywords(fileId: int, keywords: List[str], db: Session = Depends(get_db)) -> DetailedResponse:
    file_exists = db.execute(select(File_Model).filter_by(FI_ID=fileId)).scalars().first()
    if not file_exists:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        new_keywords: List[File_Keyword]
        for keyword in keywords:
            new_keyword = File_Keyword(FI_ID=fileId, Keyword=keyword)
            new_keywords.append(new_keyword)
            db.add(new_keyword)
        db.commit()
        return DetailedResponse(code=201, message="Correctly saved", data=new_keywords)
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return DetailedResponse(code=500, message="Error", error=str(e))

@router.post("/save-chat-history", tags=["crud_etap3"], response_model=DetailedResponse)
async def save_chat_history(prompt: str, answer: str, file_id: Optional[int] = None,  db: Session = Depends(get_db)) -> DetailedResponse:
    if file_id is not None:
        file_exists = db.execute(select(File_Model).filter_by(FI_ID=file_id)).scalars().first()
        if not file_exists:
            raise HTTPException(status_code=404, detail="File not found")

    try:
        llm_message = LLM_Message(Prompt=prompt, Answer=answer, FI_ID=file_id)
        db.add(llm_message)
        db.commit()
        return DetailedResponse(code=201, message="Correctly saved", data=LLMMessageResponse.from_orm(llm_message))
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return DetailedResponse(code=500, message="Error", error=str(e))

@router.patch("/save-corrected-text", tags=["crud_etap2"], response_model=DetailedResponse)
async def save_corrected_text(fileId: int, corrected_text: str, db: Session = Depends(get_db)) -> DetailedResponse:
    file_instance  =  db.execute(select(File_Model).filter_by(FI_ID=fileId)).scalars().first()
    if not file_instance :
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_instance.Corretted_Content = corrected_text
        db.commit()

        return DetailedResponse(code=201, message="Correctly updated", data=FileModelResponse.from_orm(file_instance))
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error occurred: {e}")
        return DetailedResponse(code=500, message="Error", error=str(e))