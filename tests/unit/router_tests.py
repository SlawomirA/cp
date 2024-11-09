import pytest
from unittest.mock import MagicMock, patch

from main import app
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO


client = TestClient(app)


def create_sample_upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


@pytest.fixture
def sample_pdf_file():
    return create_sample_upload_file("test.pdf", b"%PDF-1.4 sample content")


@patch("src.pdf.router.requests.get")
def test_download_pdf(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"%PDF-1.4\n%...\n"

    response = client.get("/download-pdf/",
                          params={"url": "www.example.com/sample.pdf"})

    assert response.status_code == 200
    assert response.json()["message"] == "PDF downloaded successfully"
    assert "file_path" in response.json()


@patch("src.pdf.router.requests.get")
def test_download_pdf_failure(mock_get):
    mock_get.return_value.status_code = 500
    response = client.get("/download-pdf/",
                          params={"url": "www.example.com/sample.pdf"})

    assert response.status_code == 500
    assert response.json()["detail"] == "500: Failed to download the PDF."


@patch("src.pdf.router.requests.get")
def test_download_pdf_return_base64(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"%PDF-1.4\n%...\n"
    response = client.get("/download-pdf-return/",
                          params={"url": "www.example.com/file.pdf"})

    assert "pdf" in response.json()


@patch("src.pdf.router.requests.get")
def test_download_pdf_return_base64_failure(mock_get):
    mock_get.return_value.status_code = 500
    response = client.get("/download-pdf-return/",
                          params={"url": "www.example.com/file.pdf"})

    assert response.status_code == 500
    assert response.json()["detail"] == "500: Failed to download the PDF."


@patch("src.pdf.router.subprocess.Popen")
def test_scrape_pdfs(mock_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"stdout", b"")
    mock_popen.return_value = mock_process
    response = client.get("/scrape-pdfs/",
                          params={"start_url": "www.example.com"})
    assert response.status_code == 200
    assert "message" in response.json() or "pdf_links" in response.json()


@patch("src.pdf.router.subprocess.Popen")
def test_scrape_pdfs_failure(mock_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"stderr")
    mock_popen.return_value = mock_process
    response = client.get("/scrape-pdfs/",
                          params={"start_url": "www.example.com"})
    assert response.status_code == 500
    assert "detail" in response.json()


@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
def test_upload_pdf(mock_image_to_string, mock_convert_from_path, sample_pdf_file):
    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]

    response = client.post("/ocr-pdf", files={
        "file": ("test.pdf", sample_pdf_file.file, "application/pdf")})
    assert response.status_code == 200
    assert response.text == "Extracted text"


@patch("src.pdf.router.convert_from_path")
@patch("src.pdf.router.pytesseract.image_to_string")
def test_upload_pdf_failure(mock_image_to_string, mock_convert_from_path, sample_pdf_file):
    mock_image_to_string.return_value = "Extracted text"
    mock_convert_from_path.return_value = [MagicMock()]

    response = client.post("/ocr-pdf", files={
        "file": ("test.txt", sample_pdf_file.file, "application/pdf")})
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are allowed."


@patch("src.pdf.router.tool.correct")
def test_correct_text(mock_correct):
    mock_correct.return_value = "Corrected text"
    response = client.post("/correct-text",
                           json={"input_text": "Ducibus meis"})

    assert response.status_code == 200
    assert response.json()["original_text"] == "Ducibus meis"
    assert response.json()["corrected_text"] == "Corrected text"


@patch("src.pdf.router.tool.correct")
def test_correct_text_failure(mock_correct):
    mock_correct.side_effect = Exception("Some error")
    response = client.post("/correct-text",
                           json={"input_text": "Ducibus meis"})
    assert response.status_code == 500
    assert "detail" in response.json()
    assert response.json()["detail"] == "Error processing the text: Some error"


@patch("src.pdf.router.model.extract_keywords")
def test_extract_keywords(mock_extract_keywords):
    mock_extract_keywords.return_value = [("keyword1", 0.9), ("keyword2", 0.8)]

    response = client.post("/extract-keywords", json={
        "request": "Sample text"})
    assert response.status_code == 200
    assert "keywords" in response.json()
    assert response.json()["keywords"] == [{"keyword": "keyword1"},
                                           {"keyword": "keyword2"}]


@patch("src.pdf.router.model.extract_keywords")
def test_extract_keywords_failure(mock_extract_keywords):
    mock_extract_keywords.side_effect = Exception("Keyword extraction failed")

    response = client.post("/extract-keywords", json={
        "request": "Sample text for keyword extraction"})

    assert response.status_code == 500
    assert response.json()[
               "detail"] == "Error extracting keywords: Keyword extraction failed"
