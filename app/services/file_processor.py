import os
import logging
from typing import List, Dict, Any
from docx import Document
import PyPDF2
import mammoth
from app.services.vector_db import VectorDB

logger = logging.getLogger(__name__)

class FileProcessor:
    def __init__(self, vector_db_path: str):
        """Initialize FileProcessor with vector database path"""
        self.vector_db_path = vector_db_path
        os.makedirs(vector_db_path, exist_ok=True)

        # Initialize VectorDB with specific paths for index and documents
        self.vector_db = VectorDB(
            index_path=os.path.join(vector_db_path, "vector_index.faiss"),
            documents_path=os.path.join(vector_db_path, "documents.pkl")
        )
        logger.info(f"FileProcessor initialized with vector DB path: {vector_db_path}")

    def process_file(self, file_path: str) -> bool:
        """Process and index a file into the vector database"""
        try:
            logger.info(f"Processing file: {file_path}")
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower()

            # Extract text based on file type
            if file_ext == '.docx':
                documents = self._process_docx(file_path)
            elif file_ext == '.pdf':
                documents = self._process_pdf(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not documents:
                logger.warning(f"No text content extracted from file: {file_path}")
                return False

            logger.info(f"Extracted {len(documents)} documents from file")

            # Add each document chunk to vector database
            success_count = 0
            for idx, doc in enumerate(documents):
                document_id = f"{os.path.basename(file_path)}_{idx}"
                if self.vector_db.add_document(doc, document_id):
                    success_count += 1

            logger.info(f"Successfully indexed {success_count} chunks from {file_path}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            return False

    def _process_docx(self, file_path: str) -> List[str]:
        """Extract text from DOCX file in chunks"""
        try:
            with open(file_path, "rb") as docx_file:
                result = mammoth.extract_raw_text(docx_file)
                text = result.value

                # Split text into chunks
                chunks = self._split_text(text)
                logger.info(f"Extracted {len(chunks)} chunks from DOCX file")
                return chunks

        except Exception as e:
            logger.error(f"Error processing DOCX file {file_path}: {str(e)}", exc_info=True)
            return []

    def _process_pdf(self, file_path: str) -> List[str]:
        """Extract text from PDF file in chunks"""
        try:
            chunks = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        # Split page text into chunks
                        page_chunks = self._split_text(text)
                        chunks.extend(page_chunks)

            logger.info(f"Extracted {len(chunks)} chunks from PDF file")
            return chunks

        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {str(e)}", exc_info=True)
            return []

    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Split text into chunks of approximately equal size"""
        chunks = []
        current_chunk = []
        current_length = 0

        for paragraph in text.split('\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            if current_length + len(paragraph) > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0

            current_chunk.append(paragraph)
            current_length += len(paragraph)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def search_similar_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar documents in the vector database"""
        try:
            logger.info(f"Searching for documents similar to query: {query}")
            results = self.vector_db.search(query, top_k=top_k)
            logger.info(f"Found {len(results)} similar documents")
            return results
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}", exc_info=True)
            return []