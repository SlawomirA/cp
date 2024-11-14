import json

import pytest
from unittest.mock import MagicMock, patch

from fastapi import UploadFile
from io import BytesIO

from src.models import File_Model


def create_sample_upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


@pytest.fixture
def sample_pdf_file():
    return create_sample_upload_file("test.pdf", b"%PDF-1.4 sample content")


@patch("src.pdf.router.requests.get")
def test_download_pdf(mock_get, client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"%PDF-1.4\n%...\n"

    response = client.get("/download-pdf/",
                          params={"url": "www.example.com/sample.pdf"})

    assert response.status_code == 200
    assert response.json()["message"] == "PDF downloaded successfully"
    assert "file_path" in response.json()


@patch("src.pdf.router.requests.get")
def test_download_pdf_failure(mock_get, client):
    mock_get.return_value.status_code = 500
    response = client.get("/download-pdf/",
                          params={"url": "www.example.com/sample.pdf"})

    assert response.status_code == 500
    assert response.json()["detail"] == "500: Failed to download the PDF."


@patch("src.pdf.router.requests.get")
def test_download_pdf_return_base64(mock_get, client):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"%PDF-1.4\n%...\n"
    response = client.get("/download-pdf-return/",
                          params={"url": "www.example.com/file.pdf"})

    assert "pdf" in response.json()


@patch("src.pdf.router.requests.get")
def test_download_pdf_return_base64_failure(mock_get, client):
    mock_get.return_value.status_code = 500
    response = client.get("/download-pdf-return/",
                          params={"url": "www.example.com/file.pdf"})

    assert response.status_code == 500
    assert response.json()["detail"] == "500: Failed to download the PDF."


@patch("src.pdf.router.subprocess.Popen")
def test_scrape_pdfs(mock_popen, client):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"stdout", b"")
    mock_popen.return_value = mock_process
    response = client.get("/scrape-pdfs/",
                          params={"start_url": "http://www.example.com"})
    assert response.status_code == 200
    assert "message" in response.json() or "pdf_links" in response.json()


@patch("src.pdf.router.subprocess.Popen")
def test_scrape_pdfs_invalid_url(mock_popen, client):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"stdout", b"")
    mock_popen.return_value = mock_process
    response = client.get("/scrape-pdfs/",
                          params={"start_url": "www.example.com"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL: Missing 'http://' or 'https://' scheme."
    assert "detail" in response.json()


@patch("src.pdf.router.subprocess.Popen")
def test_scrape_pdfs_failure(mock_popen, client):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"stderr")
    mock_popen.return_value = mock_process
    response = client.get("/scrape-pdfs/",
                          params={"start_url": "http://www.example.com"})
    assert response.status_code == 500
    assert "detail" in response.json()


@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
def test_upload_pdf(mock_image_to_string, mock_convert_from_path, client, sample_pdf_file):
    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]

    response = client.post("/ocr-pdf", files={
        "file": ("test.pdf", sample_pdf_file.file, "application/pdf")})
    assert response.status_code == 200
    assert response.text == "Extracted text"


def test_upload_pdf_not_pdf(client, sample_pdf_file):
    response = client.post("/ocr-pdf", files={
        "file": ("test.txt", sample_pdf_file.file, "application/pdf")})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


@patch("src.pdf.router.convert_from_path")
def test_upload_pdf_failure(mock_convert_from_path, client, sample_pdf_file):
    mock_convert_from_path.side_effect = Exception("Conversion error")
    response = client.post("/ocr-pdf", files={
        "file": ("test.pdf", sample_pdf_file.file, "application/pdf")
    })
    assert response.status_code == 500
    assert response.json()["detail"] == "Conversion error"


@patch("src.pdf.router.tool.correct")
def test_correct_text(mock_correct, client):
    mock_correct.return_value = "Corrected text"
    response = client.post("/correct-text",
                           json={"input_text": "Ducibus meis"})

    assert response.status_code == 200
    assert response.json()["original_text"] == "Ducibus meis"
    assert response.json()["corrected_text"] == "Corrected text"


@patch("src.pdf.router.tool.correct")
def test_correct_text_failure(mock_correct, client):
    mock_correct.side_effect = Exception("Some error")
    response = client.post("/correct-text",
                           json={"input_text": "Ducibus meis"})
    assert response.status_code == 500
    assert "detail" in response.json()
    assert response.json()["detail"] == "Error processing the text: Some error"

@patch("src.pdf.router.Engine")
def test_ask_for_advice_db(mock_engine, client, db_session):
    file_record = File_Model(FI_ID=1, Content="content")
    db_session.add(file_record)
    db_session.commit()

    mock_engine = mock_engine.return_value
    mock_engine.connection.return_value = json.dumps({"results": [{"text": "Advice"}]})
    mock_engine.create_prompt.return_value = "prompt"
    response = client.post("/ask-for-advice", params={"fileId": 1, "question": "question"})
    assert response.status_code == 200
    assert "prompt" in response.json()
    assert "answer" in response.json()


@patch("src.pdf.router.Engine")
def test_ask_for_advice_db_error_handling(mock_engine, client, db_session):
    file_record = File_Model(FI_ID=1, Content="content")
    db_session.add(file_record)
    db_session.commit()

    mock_engine = mock_engine.return_value
    mock_engine.connection.side_effect = Exception("Some error")
    response = client.post("/ask-for-advice", params={"fileId": 1, "question": "question"})
    assert response.status_code == 500
    assert "detail" in response.json()


@patch("src.pdf.router.Engine")
@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
def test_ask_for_advice_file(mock_image_to_string, mock_convert_from_path, mock_engine, client, db_session, sample_pdf_file):
    mock_engine = mock_engine.return_value
    mock_engine.connection.return_value = json.dumps({"results": [{"text": "Advice"}]})
    mock_engine.create_prompt.return_value = "prompt"

    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]

    response = client.post("/ask-for-advice", files={"input_file": ("test.pdf", sample_pdf_file.file, "application/pdf")}, params={"question": "question"})
    assert response.status_code == 200
    assert "prompt" in response.json()
    assert "answer" in response.json()


@patch("src.pdf.router.Engine")
def test_ask_for_advice_invalid_file_type(mock_engine, client, sample_pdf_file):
    mock_engine = mock_engine.return_value
    mock_engine.connection.return_value = json.dumps({"results": [{"text": "Advice"}]})
    mock_engine.create_prompt.return_value = "prompt"
    response = client.post("/ask-for-advice", files={"input_file": ("test.txt", sample_pdf_file.file, "text/plain")}, params={"question": "question"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


@patch("src.pdf.router.Engine")
def test_ask_for_advice_file_error_handling(mock_engine, client, db_session, sample_pdf_file):
    mock_engine = mock_engine.return_value
    mock_engine.connection.return_value = json.dumps({"results": [{"text": "Advice"}]})
    mock_engine.create_prompt.return_value = "prompt"

    mock_engine.connection.side_effect = Exception("Some error")
    response = client.post("/ask-for-advice", files={"input_file": ("test.pdf", sample_pdf_file.file, "application/pdf")}, params={"question": "question"})
    assert response.status_code == 500
    assert "detail" in response.json()


@patch("src.pdf.router.model.extract_keywords")
def test_extract_keywords(mock_extract_keywords, client):
    mock_extract_keywords.return_value = [("keyword1", 0.9), ("keyword2", 0.8)]

    response = client.post("/extract-keywords", json={
        "request": "Sample text"})
    assert response.status_code == 200
    assert "keywords" in response.json()
    assert response.json()["keywords"] == [{"keyword": "keyword1"},
                                           {"keyword": "keyword2"}]


@patch("src.pdf.router.model.extract_keywords")
def test_extract_keywords_failure(mock_extract_keywords, client):
    mock_extract_keywords.side_effect = Exception("Keyword extraction failed")

    response = client.post("/extract-keywords", json={
        "request": "Sample text for keyword extraction"})

    assert response.status_code == 500
    assert response.json()[
               "detail"] == "Error extracting keywords: Keyword extraction failed"


@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
@patch("src.pdf.router.tool.correct")
@patch("src.pdf.router.model.extract_keywords")
def test_load_pdf_data(mock_extract_keywords, mock_correct, mock_image_to_string, mock_convert_from_path, client, db_session, sample_pdf_file):
    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]
    mock_correct.return_value = "Corrected text"
    mock_extract_keywords.return_value = [("keyword1", 0.9), ("keyword2", 0.8)]

    response = client.post("/load-pdf-data", files={"file": ("test.pdf", sample_pdf_file.file, "application/pdf")}, params={"url": "http://example.com/test.pdf"})
    assert response.status_code == 200
    assert response.json()["code"] == 201
    assert response.json()["message"] == "File successfully saved"
    assert "data" in response.json()

    saved_file = db_session.query(File_Model).filter_by(Name="test.pdf").first()
    assert saved_file is not None
    assert saved_file.Corretted_Content == "Corrected text"


def test_load_pdf_data_invalid_file_type(client, sample_pdf_file):
    response = client.post("/load-pdf-data", files={"file": ("test.txt", sample_pdf_file.file, "text/plain")}, params={"url": "http://example.com/test.pdf"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
@patch("src.pdf.router.tool.correct")
@patch("src.pdf.router.model.extract_keywords")
def test_load_pdf_data_error_handling(mock_extract_keywords, mock_correct, mock_image_to_string, mock_convert_from_path, client, db_session, sample_pdf_file):
    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]
    mock_correct.return_value = "Corrected text"
    mock_extract_keywords.return_value = [("keyword1", 0.9), ("keyword2", 0.8)]
    db_session.commit = MagicMock(side_effect=Exception("Some error"))
    response = client.post("/load-pdf-data", files={"file": ("test.pdf", sample_pdf_file.file, "application/pdf")}, params={"url": "http://example.com/test.pdf"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Error occurred while saving the file"

    saved_file = db_session.query(File_Model).filter_by(Name="test.pdf").first()
    assert saved_file is None
