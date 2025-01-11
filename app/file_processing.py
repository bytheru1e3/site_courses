import os
from typing import List, Dict, Union, Any
import PyPDF2
from docx import Document
import logging

logger = logging.getLogger(__name__)

def process_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Обработать файл и извлечь из него текст.
    Поддерживает форматы PDF и DOCX.
    """
    try:
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return process_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return process_docx(file_path)
        else:
            logger.error(f"Unsupported file format: {file_extension}")
            return []
            
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return []

def process_pdf(file_path: str) -> List[Dict[str, Any]]:
    """Извлечь текст из PDF файла"""
    try:
        documents = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                text = pdf_reader.pages[page_num].extract_text()
                if text.strip():
                    documents.append({
                        'text': text.strip(),
                        'page': page_num + 1,
                        'source': file_path
                    })
        return documents
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")
        return []

def process_docx(file_path: str) -> List[Dict[str, Any]]:
    """Извлечь текст из DOCX файла"""
    try:
        documents = []
        doc = Document(file_path)
        for para_num, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if text:
                documents.append({
                    'text': text,
                    'paragraph': para_num + 1,
                    'source': file_path
                })
        return documents
    except Exception as e:
        logger.error(f"Error processing DOCX {file_path}: {str(e)}")
        return []
