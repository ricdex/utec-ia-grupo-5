"""
RAG (Retrieval-Augmented Generation) Manager
Processes product PDFs and retrieves relevant information for portfolio recommendations
"""

import json
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class Document:
    """Represents a document chunk from a product PDF"""
    doc_id: str
    product_name: str
    chunk_index: int
    content: str
    metadata: Dict
    hash: str


class PDFExtractor:
    """Extract text from PDF documents"""

    @staticmethod
    def extract_text_from_pdf(pdf_content: bytes) -> str:
        """
        Extract text from PDF content
        In production, use pypdf2 or pdfplumber
        For now, this is a placeholder
        """
        # In production with Lambda, you would use:
        # import pypdf
        # reader = pypdf.PdfReader(BytesIO(pdf_content))
        # text = ""
        # for page in reader.pages:
        #     text += page.extract_text()
        # return text

        # For testing, return structured product info
        return "Fondo ZEST Deuda Privada - Retorno 6.5%-7.5% anual, cupón mensual, liquidez trimestral"


class DocumentChunker:
    """Split documents into chunks for embedding"""

    @staticmethod
    def chunk_document(
        text: str,
        product_name: str,
        chunk_size: int = 300,
        overlap: int = 50
    ) -> List[str]:
        """
        Split document into overlapping chunks
        """
        chunks = []
        sentences = re.split(r'[.!?]+', text)

        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence exceeds chunk size
            if len(current_chunk) + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    # Keep overlap
                    words = current_chunk.split()
                    overlap_words = words[-int(len(words) * 0.2):]
                    current_chunk = " ".join(overlap_words) + " " + sentence
                else:
                    chunks.append(sentence)
                    current_chunk = ""
            else:
                current_chunk += " " + sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    @staticmethod
    def add_product_context(chunks: List[str], product_name: str) -> List[str]:
        """Add product name context to each chunk"""
        return [f"[{product_name}] {chunk}" for chunk in chunks]


class SimpleEmbedding:
    """
    Simple embedding generator using TF-IDF style vector
    In production, use sentence-transformers or OpenAI embeddings
    """

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization"""
        # Remove special characters and split
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        return tokens

    @staticmethod
    def _build_vocabulary(documents: List[str]) -> Tuple[Dict[str, int], int]:
        """Build vocabulary from documents"""
        vocab = {}
        for doc in documents:
            tokens = SimpleEmbedding._tokenize(doc)
            for token in tokens:
                if token not in vocab:
                    vocab[token] = len(vocab)
        return vocab, len(vocab)

    @staticmethod
    def generate_embedding(text: str, vocab: Optional[Dict[str, int]] = None) -> List[float]:
        """
        Generate simple embedding vector based on term frequency
        Returns normalized frequency vector
        """
        tokens = SimpleEmbedding._tokenize(text)
        freq = {}

        for token in tokens:
            freq[token] = freq.get(token, 0) + 1

        # Convert to vector (use hash for consistency)
        # This is a simplified approach
        vector = []
        for token in sorted(set(tokens))[:100]:  # Limit to 100 dimensions
            hash_val = int(hashlib.md5(token.encode()).hexdigest(), 16) % 1000
            vector.append((hash_val, freq.get(token, 0)))

        # Normalize
        total = sum(v[1] for v in vector) or 1
        normalized = [float(v[1]) / total for v in vector]

        return normalized[:100]  # Return first 100 dimensions

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        # Pad vectors to same length
        max_len = max(len(vec1), len(vec2))
        v1 = vec1 + [0] * (max_len - len(vec1))
        v2 = vec2 + [0] * (max_len - len(vec2))

        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = sum(a * a for a in v1) ** 0.5
        magnitude2 = sum(a * a for a in v2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


class RAGStorage:
    """Storage backend for documents and embeddings"""

    def __init__(self):
        # In-memory storage for RAG documents
        # Products are loaded from CSV and stored here for fast semantic search
        self.documents: Dict[str, Document] = {}
        self.embeddings: Dict[str, List[float]] = {}

    def store_document(self, doc: Document, embedding: List[float]):
        """Store document and its embedding"""
        self.documents[doc.doc_id] = doc
        self.embeddings[doc.doc_id] = embedding

    def retrieve_documents(self, query: str, top_k: int = 3) -> List[Tuple[Document, float]]:
        """Retrieve top-k documents most relevant to query"""
        query_embedding = SimpleEmbedding.generate_embedding(query)

        # Calculate similarity with all documents
        similarities = []
        for doc_id, doc in self.documents.items():
            embedding = self.embeddings.get(doc_id, [])
            similarity = SimpleEmbedding.cosine_similarity(query_embedding, embedding)
            similarities.append((doc, similarity))

        # Sort by similarity and return top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    def get_product_documents(self, product_name: str) -> List[Document]:
        """Get all documents for a specific product"""
        return [
            doc for doc in self.documents.values()
            if doc.product_name == product_name
        ]


class RAGManager:
    """Main RAG Manager orchestrating document processing and retrieval"""

    def __init__(self):
        self.storage = RAGStorage()
        self.extractor = PDFExtractor()
        self.chunker = DocumentChunker()

    def add_document(self, product_data: Dict) -> None:
        """
        Add a product document directly to RAG (from CSV or structured data)
        Used by seed_rag.py script for initialization

        Args:
            product_data: Dictionary containing product info with 'text' field
        """
        product_id = product_data.get('product_id', 'unknown')
        product_name = product_data.get('product_name', 'Unknown Product')
        text = product_data.get('text', '')

        # Create document ID
        doc_type = product_data.get('document_type', 'info')
        doc_id = f"{product_id}_{doc_type}"
        doc_hash = hashlib.md5(text.encode()).hexdigest()

        # Create document
        document = Document(
            doc_id=doc_id,
            product_name=product_name,
            chunk_index=0,
            content=text,
            metadata={k: v for k, v in product_data.items() if k != 'text'},
            hash=doc_hash
        )

        # Generate embedding and store
        embedding = SimpleEmbedding.generate_embedding(text)
        self.storage.store_document(document, embedding)

    def ingest_product_document(
        self,
        pdf_content: bytes,
        product_name: str,
        product_id: str,
        metadata: Dict
    ) -> int:
        """
        Ingest a product document into the RAG system
        Returns number of chunks created
        """

        # Extract text from PDF
        text = self.extractor.extract_text_from_pdf(pdf_content)

        # Split into chunks
        chunks = self.chunker.chunk_document(text, product_name)

        # Add product context
        chunks = self.chunker.add_product_context(chunks, product_name)

        # Store chunks with embeddings
        for i, chunk in enumerate(chunks):
            doc_id = f"{product_id}_chunk_{i}"
            doc_hash = hashlib.md5(chunk.encode()).hexdigest()

            document = Document(
                doc_id=doc_id,
                product_name=product_name,
                chunk_index=i,
                content=chunk,
                metadata={**metadata, "chunk_index": i},
                hash=doc_hash
            )

            embedding = SimpleEmbedding.generate_embedding(chunk)
            self.storage.store_document(document, embedding)

        return len(chunks)

    def search_products(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Search for product information relevant to query
        Returns list of relevant document excerpts
        """
        retrieved_docs = self.storage.retrieve_documents(query, top_k)

        results = []
        for doc, score in retrieved_docs:
            results.append({
                "product_name": doc.product_name,
                "content": doc.content,
                "relevance_score": score,
                "metadata": doc.metadata
            })

        return results

    def get_product_summary(self, product_name: str) -> str:
        """Get summary of product from stored documents"""
        product_docs = self.storage.get_product_documents(product_name)

        if not product_docs:
            return f"No information found for {product_name}"

        # Combine first few chunks as summary
        summary_chunks = [doc.content for doc in product_docs[:3]]
        return " ".join(summary_chunks)

    def augment_recommendation_context(
        self,
        client_profile: Dict,
        eligible_products: List[Dict]
    ) -> str:
        """
        Create augmented context for recommendation based on RAG search
        """
        context = "## Información de Productos (RAG):\n"

        for product in eligible_products[:3]:  # Limit to top 3
            summary = self.get_product_summary(product.get("name", ""))
            if summary:
                context += f"\n**{product.get('name')}**:\n{summary}\n"

        # Search for specific investment strategies based on profile
        query = f"inversión {client_profile.get('risk_profile', 'moderado')} plazo {client_profile.get('investment_horizon_months', 24)} meses"
        search_results = self.search_products(query, top_k=2)

        if search_results:
            context += "\n## Recomendaciones Específicas:\n"
            for result in search_results:
                context += f"- {result['product_name']}: {result['content'][:200]}...\n"

        return context


class RAGProductDatabase:
    """Product database helper for RAG initialization"""

    @staticmethod
    def initialize_empty(rag_manager: RAGManager):
        """
        Initialize RAG with empty database
        Products should be loaded from CSV files via seed_rag.py script
        """
        return rag_manager

    @staticmethod
    def initialize_sample_products(rag_manager: RAGManager):
        """
        Initialize RAG with sample product data
        DEPRECATED: Use seed_rag.py to load from CSV files instead

        This method is kept for backward compatibility but should not be used
        in production. Use data/products_info.csv and data/product_structure.csv
        with the seed_rag.py script instead.
        """

        # Sample product documents based on actual products
        sample_products = [
            {
                "id": "PROD_ZEST_DEUDA",
                "name": "ZEST Deuda Privada",
                "content": """
                FONDO ZEST DEUDA PRIVADA - JUNIO 2025

                Descripción:
                Fondo de fondos multi gestor enfocado en invertir en préstamos de compañías
                privadas estadounidenses con enfoque defensivo.

                Características Principales:
                - Retorno esperado: 6.5% - 7.5% anual (cupón neto esperado)
                - Distribución: Mensual (cupón)
                - Liquidez: Trimestral a partir del primer año cumplido (5% máximo del fondo)
                - Comisión anual: 1.69% + IGV del valor del fondo
                - Período mínimo: 1 año desde emisión de cuotas
                - Moneda: USD

                Gestoras de Primer Nivel:
                Blackstone: USD 1,170 B patrimonio administrado
                - 38 años experiencia en alternativos
                - USD 376 B en crédito privado
                - 20 años en financiamiento privado

                Apollo: USD 785 B patrimonio administrado
                - 33 años experiencia en alternativos
                - USD 616 B en crédito privado
                - 32 años en financiamiento privado

                Estructura del Fondo:
                - Fondo Deuda Privada BCRED: USD 72.3B patrimonio
                  - 97% deuda senior con colateral
                  - 2.3x colateral sobre valor del préstamo

                - Fondo Deuda Privada ADS: USD 18.8B patrimonio
                  - 100% deuda senior con colateral
                  - 2.5x colateral sobre valor del préstamo

                Principales Industrias (Composición):
                - Software: 17.3%
                - Servicios de Salud: 8.1%
                - Servicios Comerciales: 6.6%
                - Aseguradoras: 5.7%
                - Servicios Profesionales: 4.4%

                Auditor: PwC Perú
                Domicilio: Perú
                Suscripción: Diaria

                Ventajas:
                - Diversificación sobre inversiones tradicionales
                - Enfoque en mercados desarrollados (principalmente EEUU)
                - Estabilidad en la inversión con gestoras de primer nivel
                - Distribución recurrente mensual
                """,
                "metadata": {
                    "type": "moderado",
                    "liquidity": "media",
                    "currency": "USD",
                    "jurisdiction": "Perú",
                    "annual_rate": 0.070,
                    "min_months": 12,
                    "distribution": "monthly"
                }
            },
            {
                "id": "PROD_ZEST_BOND_CG2",
                "name": "Zest Bond Liquid CG2",
                "content": """
                ZEST BOND LIQUID - SERIE CG2

                Descripción:
                Nota estructurada de renta trimestral garantizada con mecanismo Autocall.
                Depende de la acción de menor rendimiento para determinar devolución del capital.

                Características:
                - Cupón: 2.625% trimestral (garantizado)
                - Plazo: 8 períodos trimestrales (2 años aprox.)
                - Vencimiento: 11 Octubre 2027
                - Observación final: 20 Septiembre 2027
                - Moneda: USD
                - ISIN: XS3126376857

                Estructura de Pagos:
                - 8 cupones de 2.625% cada uno
                - Transferencias trimestrales a cuenta bancaria
                - Pagos garantizados sin importar rendimiento de subyacentes

                Mecanismo Autocall:
                - Precio Autocall: 100% del precio de entrada
                - Si menor subyacente > Autocall en mes de observación: producto termina anticipadamente
                - Inversionista recibe 100% capital + cupones generados
                - Fechas de observación: M1, M4, M7 (con cupones en M1-M8)

                Escenarios al Vencimiento:

                Escenario 1 (Mejor caso):
                - Si menor subyacente > barrera capital (50%) al vencimiento
                - Recibe: 100% capital invertido + todos los cupones (8 x 2.625% = 21%)

                Escenario 2 (Ejecución capital):
                - Si menor subyacente cae por debajo barrera capital
                - Recibe: Acciones al valor de mercado + cupones generados
                - Riesgo: Exposición a precio de subyacente de menor rendimiento

                Escenario 3 (Autocall - Temprana ejecución):
                - Si condición Autocall se cumple antes de vencimiento
                - Término anticipado, devolución capital + cupones hasta esa fecha

                Subyacentes:
                1. Agnico Eagle Mines Ltd (AEM.UN)
                   - Canadá (1953)
                   - Empresa extractora de oro, exploración y producción de metales preciosos
                   - Minas en: Canadá, Australia, Finlandia, México
                   - Precio entrada: USD 161.19 | Barrera: USD 80.595
                   - Capitalización 2024: USD 80.94 B

                2. Arista Networks Inc (ANET.UN)
                   - California, Estados Unidos (2004)
                   - Empresa de redes en la nube, soluciones datacenter
                   - Productos: enrutamiento avanzado, software supervisión, análisis seguridad
                   - Precio entrada: USD 149.61 | Barrera: USD 74.805
                   - Capitalización 2024: USD 182.91 B

                3. Meta Platforms Inc (META.UW)
                   - California, Estados Unidos (2004)
                   - Tecnología de conectividad y comunidades
                   - Productos: conectividad, compartir, realidad virtual
                   - Precio entrada: USD 778.38 | Barrera: USD 389.19
                   - Capitalización 2024: USD 1,930.30 B

                4. NVIDIA Corp (NVDA.UW)
                   - California, Estados Unidos (1993)
                   - Líder en tecnología: computación, IA, gráficos
                   - Especialización: GPUs para gaming, datacenters, aplicaciones industriales
                   - Innovación en: IA, conducción autónoma, computación nube
                   - Precio entrada: USD 176.67 | Barrera: USD 88.335
                   - Capitalización 2024: USD 465.273 B

                Riesgos:
                - Volatilidad del precio de acciones (subyacentes)
                - Riesgo de ejecución de capital si barrera se quiebra
                - Riesgo de concentración en subyacentes de menor rendimiento

                Barrera Europea: Capital 50%
                Custodia: Pershing LLC
                Emisor: BBVA
                """,
                "metadata": {
                    "type": "moderado",
                    "liquidity": "media",
                    "currency": "USD",
                    "product_type": "structured_note",
                    "coupon_frequency": "quarterly",
                    "annual_coupon": 0.0525,  # 2.625% x 2 per year
                    "maturity_months": 24,
                    "capital_barrier": 0.50
                }
            }
        ]

        for product in sample_products:
            rag_manager.ingest_product_document(
                pdf_content=product["content"].encode(),
                product_name=product["name"],
                product_id=product["id"],
                metadata=product["metadata"]
            )

        return rag_manager


if __name__ == "__main__":
    # Test RAG Manager
    rag = RAGManager()

    # Initialize with sample products
    rag = RAGProductDatabase.initialize_sample_products(rag)

    # Test search
    query = "fondo deuda privada retorno mensual"
    results = rag.search_products(query)

    print(f"Search results for '{query}':")
    for result in results:
        print(f"- {result['product_name']}: {result['relevance_score']:.2f}")
        print(f"  {result['content'][:100]}...")

    # Test augmented context
    client = {
        "risk_profile": "moderado",
        "investment_horizon_months": 24
    }
    products = [{"name": "ZEST Deuda Privada"}]

    context = rag.augment_recommendation_context(client, products)
    print(f"\nAugmented Context:\n{context}")
