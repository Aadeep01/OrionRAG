import logging

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiClient:
    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)  # type: ignore[attr-defined]
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)  # type: ignore[attr-defined]
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL

    async def get_embeddings(self, text: str) -> list[float]:
        """Generate embeddings for a single text string"""
        try:
            result = genai.embed_content(  # type: ignore[attr-defined]
                model=self.embedding_model, content=text, task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e!s}")
            raise

    async def get_query_embedding(self, text: str) -> list[float]:
        """Generate embeddings for a query"""
        try:
            result = genai.embed_content(  # type: ignore[attr-defined]
                model=self.embedding_model, content=text, task_type="retrieval_query"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e!s}")
            raise

    async def generate_content(self, prompt: str, context: str = "") -> str:
        """Generate content using Gemini"""
        try:
            full_prompt = f"""
            Context information is below.
            ---------------------
            {context}
            ---------------------
            Given the context information and not prior knowledge, answer the query.
            Query: {prompt}
            Answer:
            """

            response = self.model.generate_content(full_prompt)
            return str(response.text)
        except Exception as e:
            logger.error(f"Failed to generate content: {e!s}")
            raise

    async def extract_text_from_image(self, image_data: bytes, mime_type: str) -> str:
        """Extract text from image using Gemini Vision capabilities"""
        try:
            image_part = {"mime_type": mime_type, "data": image_data}

            prompt = (
                "Extract all text from this image. Preserve formatting where possible."
            )

            response = self.model.generate_content([prompt, image_part])
            return str(response.text)
        except Exception as e:
            logger.error(f"Failed to extract text from image: {e!s}")
            raise

    async def generate_multi_queries(self, query: str, n: int = 3) -> list[str]:
        """Generate multiple variations of a query for better retrieval coverage."""
        try:
            prompt = (
                f"You are an AI language model assistant. Your task is to generate {n} "
                "different versions of the given user question to retrieve relevant "
                "documents from a vector database. By generating multiple perspectives "
                "on the user question, your goal is to help the user overcome some of "
                "the limitations of the distance-based similarity search. Provide "
                "these alternative questions separated by newlines. "
                f"Original question: {query}"
            )

            response = self.model.generate_content(prompt)
            # Split by newline and clean up
            queries = [q.strip() for q in response.text.split("\n") if q.strip()]
            # Limit to n queries just in case
            return queries[:n]
        except Exception as e:
            logger.error(f"Failed to generate multi-queries: {e!s}")
            # Fallback to just the original query if generation fails
            return [query]

    async def generate_step_back_query(self, query: str) -> str | None:
        """Generate a step-back (broader/abstract) question."""
        try:
            prompt = (
                "You are an expert at world knowledge. Your task is to step back and "
                "paraphrase a question to a more abstract, easier to answer "
                "question.\n\n"
                f"Original Question: {query}\n"
                "Step Back Question:"
            )

            response = self.model.generate_content(prompt)
            return str(response.text.strip()) if response.text else None
        except Exception as e:
            logger.error(f"Failed to generate step-back query: {e!s}")
            return None

    async def generate_hypothetical_answer(self, query: str) -> str | None:
        """Generate a hypothetical answer to the query for HyDE retrieval."""
        try:
            prompt = (
                "Please write a passage to answer the question. The passage should be "
                "a plausible answer to the question, even if you don't know the "
                "specific facts. It will be used to retrieve relevant documents "
                "based on semantic similarity.\n\n"
                f"Question: {query}\n"
                "Passage:"
            )

            response = self.model.generate_content(prompt)
            return str(response.text.strip()) if response.text else None
        except Exception as e:
            logger.error(f"Failed to generate hypothetical answer: {e!s}")
            return None

    async def rerank_documents(
        self, query: str, documents: list[str], top_n: int = 5
    ) -> list[tuple[int, float]]:
        """
        Rerank a list of documents based on their relevance to the query using Gemini.
        Returns a list of (original_index, relevance_score) tuples,
        sorted by score descending.
        """
        if not documents:
            return []

        try:
            # Construct a prompt for listwise ranking
            doc_text = ""
            for i, doc in enumerate(documents):
                # Truncate doc to avoid token limits if necessary
                doc_text += f"Document {i}:\n{doc[:1000]}...\n\n"

            prompt = (
                f"You are a relevance ranking assistant.\n"
                f"Query: {query}\n\n"
                f"Below are {len(documents)} documents. Rank them by relevance to "
                "the query.\n"
                "Assign a relevance score from 0.0 (irrelevant) to 1.0 "
                "(highly relevant) for each document.\n\n"
                "Return ONLY a list of numbers representing the scores for "
                "Document 0, Document 1, etc., in order, separated by commas.\n"
                "Example: 0.9, 0.1, 0.5\n\n"
                "Documents:\n"
                f"{doc_text}\n\n"
                "Scores:"
            )

            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Parse scores
            try:
                scores_str = text.split(",")
                scores = []
                for s in scores_str:
                    clean_s = s.strip().replace("[", "").replace("]", "")
                    if clean_s:
                        scores.append(float(clean_s))

                # Match scores to indices
                ranked_results = []
                for i in range(min(len(scores), len(documents))):
                    ranked_results.append((i, scores[i]))

                # Sort by score descending
                ranked_results.sort(key=lambda x: x[1], reverse=True)

                return ranked_results[:top_n]

            except ValueError:
                logger.error(f"Failed to parse reranking scores: {text}")
                # Fallback: return original order with default scores
                return [(i, 1.0 - (i * 0.01)) for i in range(len(documents))][:top_n]

        except Exception as e:
            logger.error(f"Failed to rerank documents: {e!s}")
            # Fallback: return original order
            return [(i, 1.0) for i in range(len(documents))][:top_n]
