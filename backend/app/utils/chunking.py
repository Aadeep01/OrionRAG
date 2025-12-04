from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


class ChunkingEngine:
    def __init__(self) -> None:
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks"""
        return self.text_splitter.split_text(text)
