import httpx
import logging
import io
import pdfplumber
from docx import Document
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentService:
    """
    Сервис для работы с тендерной документацией.
    Умеет скачивать файлы и извлекать текст из PDF и DOCX.
    """

    def __init__(self):
        self.timeout = httpx.Timeout(30.0)

    async def download_document(self, url: str) -> Optional[bytes]:
        """Скачивает документ по URL"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"Error downloading document from {url}: {e}")
            return None

    def extract_text(self, content: bytes, filename: str) -> str:
        """Определяет тип файла и извлекает текст"""
        ext = filename.split('.')[-1].lower()
        
        if ext == 'pdf':
            return self.extract_text_pdf(content)
        elif ext in ['docx', 'doc']:
            # docx library handles .docx, .doc might need different tool but usually they are docx now
            return self.extract_text_docx(content)
        else:
            logger.warning(f"Unsupported file extension: {ext}")
            return ""

    def extract_text_pdf(self, content: bytes) -> str:
        """Извлекает текст из PDF"""
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
        return text

    def extract_text_docx(self, content: bytes) -> str:
        """Извлекает текст из DOCX"""
        text = ""
        try:
            doc = Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
        return text

# Синглтон
document_service = DocumentService()
