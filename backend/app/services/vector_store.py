import logging
from typing import Any

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import (
    CollectionsResponse,
    Distance,
    VectorParams,
)

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(
        self,
        host: str,
        port: int,
        collection_name: str,
        vector_size: int = 768,
    ) -> None:
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size

    async def initialize(self) -> None:
        """Initialize the vector store collection if it doesn't exist"""
        try:
            collections: CollectionsResponse = self.client.get_collections()
            exists = any(
                c.name == self.collection_name for c in collections.collections
            )

            if not exists:
                logger.info(f"Creating collection '{self.collection_name}'...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size, distance=Distance.COSINE
                    ),
                    # Enable Scalar Quantization for 4x memory reduction
                    quantization_config=models.ScalarQuantization(
                        scalar=models.ScalarQuantizationConfig(
                            type=models.ScalarType.INT8,
                            quantile=0.99,
                            always_ram=True,
                        ),
                    ),
                    # HNSW Tuning for better recall
                    hnsw_config=models.HnswConfigDiff(
                        m=32,  # Increase links per node (default 16)
                        ef_construct=200,  # Increase candidates (default 100)
                    ),
                )

                # Create payload index for document_id to speed up filtering/deletion
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="document_id",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

                logger.info(
                    f"Collection '{self.collection_name}' created successfully "
                    "with optimizations"
                )
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e!s}")
            raise

    async def upsert_vectors(self, points: list[models.PointStruct]) -> None:
        """Upsert vectors into the collection"""
        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e!s}")
            raise

    async def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[models.ScoredPoint]:
        """Search for similar vectors"""
        try:
            # Convert dict filter to models.Filter if provided
            query_filter: models.Filter | None = None
            if filter_conditions:
                # Assuming filter_conditions follows Qdrant filter structure
                # This is a simplified conversion - adjust based on actual usage
                query_filter = models.Filter(**filter_conditions)

            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
            )
            return response.points
        except Exception as e:
            logger.error(f"Failed to search vectors: {e!s}")
            raise

    async def search_batch(
        self,
        query_vectors: list[list[float]],
        limit: int = 5,
        filter_conditions: dict[str, Any] | None = None,
    ) -> list[list[models.ScoredPoint]]:
        """
        Search for similar vectors for multiple queries in a single batch request.
        Reduces network overhead for multi-query retrieval.
        """
        try:
            # Convert dict filter to models.Filter if provided
            filter_obj: models.Filter | None = None
            if filter_conditions:
                filter_obj = models.Filter(**filter_conditions)

            requests = [
                models.QueryRequest(
                    query=qv,
                    limit=limit,
                    filter=filter_obj,
                )
                for qv in query_vectors
            ]

            # Use query_batch which is optimized for multiple queries
            responses = self.client.query_batch_points(
                collection_name=self.collection_name,
                requests=requests,
            )

            # responses is a list of QueryResponse, each containing points
            return [res.points for res in responses]

        except Exception as e:
            logger.error(f"Failed to batch search vectors: {e!s}")
            raise

    async def delete_document_vectors(self, document_id: str) -> None:
        """Delete all vectors associated with a document"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.error(f"Failed to delete document vectors: {e!s}")
            raise

    async def close(self) -> None:
        """Close connection (if needed)"""
        # Qdrant client doesn't strictly need closing for HTTP,
        # but good for cleanup if using gRPC
