from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.models import File_Model, File_Keyword


def test_save_file(client):
    data = {
        "name": "file.pdf",
        "url": "http://example.com/file.pdf",
        "content": "Some content"
    }
    response = client.post("/save-file", json=data)
    response_data = response.json()
    assert response_data["code"] == 201
    assert response_data["message"] == "File successfully saved"
    assert response_data["error"] is None
    assert "data" in response_data
    assert response_data["data"]["Name"] == data["name"]
    assert response_data["data"]["Url"] == data["url"]
    assert response_data["data"]["Content"] == data["content"]
    assert "Corretted_Content" in response_data["data"]
    assert "FI_ID" in response_data["data"]


def test_save_file_error_handling(client, db_session, mocker):
    mocker.patch("src.pdf.crud_router.save_file_to_database", side_effect=SQLAlchemyError("Database error"))
    data = {
        "name": "example.pdf",
        "url": "http://example.com/file.pdf",
        "content": "Some content here"
    }
    response = client.post("/save-file", json=data)
    assert response.status_code == 500
    assert response.json()["detail"] == "Error occurred while saving the file"


def test_file_content(client, db_session):
    file_record = File_Model(FI_ID=1, Name="file.pdf", Url="http://example.com/file.pdf", Content="Some content")
    db_session.add(file_record)
    db_session.commit()
    response = client.get("/file-content/?fileId=1")
    assert response.status_code == 200
    assert response.json()["content"] == "Some content"


def test_file_content_not_found(client, db_session):
    response = client.get("/file-content/?fileId=9999")
    assert response.status_code == 500
    assert response.json()["detail"] == "404: File not found"


def test_file_content_error_handling(client, mocker):
    mocker.patch.object(Session, "query", side_effect=SQLAlchemyError("Database error"))
    response = client.get("/file-content/?fileId=1")
    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]


def test_file_corrected_content(client, db_session):
    file_record = File_Model(FI_ID=1, Name="file.pdf", Url="http://example.com/file.pdf", Content="Some content", Corretted_Content="Some content")
    db_session.add(file_record)
    db_session.commit()
    response = client.get("/file-corrected-content/?fileId=1")
    assert response.status_code == 200
    assert response.json()["content"] == "Some content"


def test_file_corrected_content_not_found(client, db_session):
    response = client.get("/file-corrected-content/?fileId=9999")
    assert response.status_code == 500
    assert response.json()["detail"] == "404: File not found"


def test_file_corrected_content_error_handling(client, mocker):
    mocker.patch.object(Session, "query", side_effect=SQLAlchemyError("Database error"))
    response = client.get("/file-corrected-content/?fileId=1")
    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]


def test_download_corrected_txt(client, db_session):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    response = client.get("/download-corrected-txt/?fileId=1")
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == 'attachment; filename="file_corrected.txt"'
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"


def test_download_corrected_txt_not_found(client, db_session):
    response = client.get("/download-corrected-txt/?fileId=1")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_download_corrected_txt_error_handling(client, db_session, mocker):
    mocker.patch.object(Session, "query", side_effect=SQLAlchemyError("Database error"))
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()
    response = client.get("/download-corrected-txt/?fileId=1")
    assert response.status_code == 500
    assert "Database error" in response.json()["detail"]


def test_save_keywords(client, db_session):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    keywords = {
        "fileId": "1",
        "keywords": ["keyword1", "keyword2"],
    }
    response = client.post("/save-keywords", json=keywords)
    assert response.status_code == 200
    assert response.json()["code"] == 201
    assert response.json()["message"] == "Correctly saved"
    assert "data" in response.json()

    saved_keywords = db_session.query(File_Keyword).filter_by(FI_ID=1).all()
    saved_keyword_list = [k.Keyword for k in saved_keywords]
    assert set(saved_keyword_list) == set(keywords["keywords"])


def test_save_keywords_not_found(client, db_session):
    keywords = {
        "fileId": "9999",
        "keywords": ["keyword1", "keyword2"],
    }
    response = client.post("/save-keywords", json=keywords)
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_save_keywords_error_handling(client, db_session, mocker):
    mocker.patch.object(Session, "query", side_effect=SQLAlchemyError("Database error"))
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    keywords = {
        "fileId": "1",
        "keywords": ["keyword1", "keyword2"],
    }
    response = client.post("/save-keywords", json=keywords)
    assert response.status_code == 200
    assert response.json()["code"] == 500
    assert response.json()["message"] == "Error"
    assert "error" in response.json()


def test_save_chat_history(client, db_session):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    saveChatUpload = {
        "fileId": "1",
        "prompt": "prompt",
        "answer": "answer",
    }
    response = client.post("/save-chat-history", json=saveChatUpload)
    assert response.status_code == 200
    assert response.json()["code"] == 201
    assert response.json()["message"] == "Correctly saved"
    assert "data" in response.json()


def test_save_chat_history_not_found(client, db_session):
    saveChatUpload = {
        "fileId": "9999",
        "prompt": "prompt",
        "answer": "answer",
    }
    response = client.post("/save-chat-history", json=saveChatUpload)
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_save_chat_history_error_handling(client, db_session, mocker):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    saveChatUpload = {
        "fileId": "1",
        "prompt": "prompt",
        "answer": "answer",
    }
    mocker.patch.object(db_session, "add", side_effect=SQLAlchemyError("Database error"))
    response = client.post("/save-chat-history", json=saveChatUpload)
    assert response.status_code == 200
    assert response.json()["code"] == 500
    assert response.json()["message"] == "Error"
    assert "error" in response.json()


def test_save_corrected_text(client, db_session):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    SaveCorrectedTextUpload = {
        "fileId": "1",
        "corrected_text": "text"
    }
    response = client.patch("/save-corrected-text", json=SaveCorrectedTextUpload)
    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert response.json()["message"] == "OK"
    assert "data" in response.json()


def test_save_corrected_text_not_found(client, db_session):
    SaveCorrectedTextUpload = {
        "fileId": "1",
        "corrected_text": "text"
    }
    response = client.patch("/save-corrected-text", json=SaveCorrectedTextUpload)
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"


def test_save_corrected_text_error_handling(client, db_session, mocker):
    file_record = File_Model(
        FI_ID=1,
        Name="file.pdf",
        Corretted_Content="Corrected content"
    )
    db_session.add(file_record)
    db_session.commit()

    SaveCorrectedTextUpload = {
        "fileId": "1",
        "corrected_text": "text"
    }
    mocker.patch.object(db_session, "commit", side_effect=SQLAlchemyError("Database error"))
    response = client.patch("/save-corrected-text", json=SaveCorrectedTextUpload)
    assert response.status_code == 200
    assert response.json()["code"] == 400
    assert response.json()["message"] == "Error saving"
    assert "data" in response.json()
    assert "error" in response.json()
