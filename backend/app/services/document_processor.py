import logging
from pathlib import Path
from typing import Any

import docx
import pypdf
from fastapi import UploadFile

from app.services.gemini_client import GeminiClient
from app.utils.chunking import ChunkingEngine

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self, gemini_client: GeminiClient) -> None:
        self.chunking_engine = ChunkingEngine()
        self.gemini_client = gemini_client

    async def process_file(
        self, file: UploadFile, file_path: str
    ) -> list[dict[str, Any]]:
        """
        Process a file and return a list of chunks with metadata.
        """
        filename = file.filename or "unknown"
        extension = filename.split(".")[-1].lower() if "." in filename else "txt"

        text_content = ""

        try:
            if extension == "pdf":
                text_content = self._process_pdf(file_path)
            elif extension in ["docx", "doc"]:
                text_content = self._process_docx(file_path)
            elif extension == "txt":
                text_content = self._process_txt(file_path)
            elif extension in ["png", "jpg", "jpeg", "tiff"]:
                # Read file bytes for image processing
                file_bytes = Path(file_path).read_bytes()
                mime_type = file.content_type or "image/jpeg"
                text_content = await self.gemini_client.extract_text_from_image(
                    file_bytes, mime_type
                )
            else:
                # Fallback for other text-based formats
                text_content = self._process_txt(file_path)

            # Chunk the text
            chunks = self.chunking_engine.split_text(text_content)

            # Create chunk objects
            processed_chunks = []
            for i, chunk_text in enumerate(chunks):
                processed_chunks.append(
                    {
                        "chunk_index": i,
                        "content": chunk_text,
                        "metadata": {"source": filename, "type": extension},
                    }
                )

            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing file {filename}: {e!s}")
            raise

    def _process_pdf(self, file_path: str) -> str:
        text = ""
        with Path(file_path).open("rb") as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _process_docx(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def _process_txt(self, file_path: str) -> str:
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")
