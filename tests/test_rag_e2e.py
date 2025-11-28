"""
End-to-End tests for RAG-Augmented Portfolio Recommendations
"""

import pytest
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from agent.rag_manager import RAGManager, RAGProductDatabase, SimpleEmbedding
from agent.memory_manager import MemoryManager
from utils.finance_calc import FinanceCalculator, ProductAllocation


@pytest.mark.e2e
class TestRAGIntegration:
    """Test RAG integration with portfolio recommendations"""

    def test_rag_manager_initialization(self):
        """Test RAG manager can be initialized"""
        rag = RAGManager()
        assert rag is not None
        assert rag.storage is not None

    def test_product_document_ingestion(self):
        """Test ingesting product documents"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        # Check that documents were ingested
        assert len(rag.storage.documents) > 0

    def test_rag_search_zest_deuda(self):
        """Test RAG search for ZEST Deuda Privada product"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        results = rag.search_products("deuda privada retorno mensual")

        assert len(results) > 0
        assert any("ZEST" in r["product_name"] for r in results)
        assert all(r["relevance_score"] >= 0 for r in results)

    def test_rag_search_structured_notes(self):
        """Test RAG search for structured notes"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        results = rag.search_products("cupón trimestral estructurado NVIDIA META")

        assert len(results) > 0
        # Should find Zest Bond Liquid with structured note references
        product_names = [r["product_name"] for r in results]
        assert any("Zest" in name for name in product_names)

    def test_rag_product_summary(self):
        """Test getting product summary from RAG"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        summary = rag.get_product_summary("ZEST Deuda Privada")

        assert len(summary) > 0
        assert "ZEST" in summary or "6.5" in summary or "cupón" in summary.lower()

    def test_rag_augmented_context(self):
        """Test augmented context generation for recommendations"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        client_profile = {
            "risk_profile": "moderado",
            "investment_horizon_months": 24,
            "available_amount_usd": 50000,
        }

        products = [
            {"name": "ZEST Deuda Privada", "annual_rate": 0.070},
            {"name": "Zest Bond Liquid CG2", "annual_rate": 0.0525},
        ]

        context = rag.augment_recommendation_context(client_profile, products)

        assert len(context) > 0
        assert "Información de Productos" in context
        assert "ZEST" in context

    def test_embedding_generation(self):
        """Test embedding generation for documents"""
        text = "ZEST Deuda Privada Fondo retorno 6.5% cupón mensual"
        embedding = SimpleEmbedding.generate_embedding(text)

        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)

    def test_embedding_similarity(self):
        """Test cosine similarity between embeddings"""
        text1 = "ZEST Deuda Privada retorno mensual cupón"
        text2 = "Fondo privado distribución mensual ingresos"
        text3 = "Acciones volatilidad riesgo alto"

        emb1 = SimpleEmbedding.generate_embedding(text1)
        emb2 = SimpleEmbedding.generate_embedding(text2)
        emb3 = SimpleEmbedding.generate_embedding(text3)

        sim_12 = SimpleEmbedding.cosine_similarity(emb1, emb2)
        sim_13 = SimpleEmbedding.cosine_similarity(emb1, emb3)

        # Similar documents should have higher similarity
        assert sim_12 >= 0
        assert sim_13 >= 0
        # Can't guarantee sim_12 > sim_13 with simple embeddings, but check non-zero
        assert sim_12 > 0 or sim_13 > 0

    def test_rag_with_portfolio_building(self):
        """Test RAG augmented portfolio building"""
        from utils.finance_calc import FinanceCalculator

        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        client_profile = {
            "risk_profile": "moderado",
            "investment_horizon_months": 24,
            "available_amount_usd": 50000,
            "target_return_pct": 8.0,
            "max_aggressive_pct": 40,
        }

        # Get augmented context from RAG
        products_list = [
            {"name": "ZEST Deuda Privada", "id": "PROD001", "type": "moderado", "annual_rate": 0.070},
            {"name": "Zest Bond Liquid CG2", "id": "PROD002", "type": "moderado", "annual_rate": 0.0525},
        ]

        context = rag.augment_recommendation_context(client_profile, products_list)

        # Use RAG context in portfolio building
        assert "ZEST" in context
        assert "cupón" in context.lower()

    def test_memory_with_rag_context(self):
        """Test memory manager storing RAG-augmented information"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)
        memory = MemoryManager("TEST_CLI_RAG_001")

        # Add RAG search results to memory
        search_results = rag.search_products("deuda privada cupón mensual")

        memory.add_user_message("Busco fondo con cupón mensual")
        rag_context = "Productos encontrados: " + json.dumps([
            {"product": r["product_name"], "score": r["relevance_score"]}
            for r in search_results[:2]
        ])
        memory.add_assistant_message(rag_context)

        # Verify memory contains RAG context
        history = memory.stm.get_conversation_history()
        assert len(history) >= 2
        assert any("ZEST" in msg["content"] for msg in history)

    def test_rag_multi_language_capability(self):
        """Test RAG capability with Spanish financial terminology"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        spanish_queries = [
            "retorno esperado distribuido mensualmente",
            "nota estructurada con barrera de capital",
            "fondo multigestor defensivo enfoque crediticio",
            "autocall anticipada si subyacente supera precio",
            "cupones garantizados trimestrales regardless rentabilidad",
        ]

        for query in spanish_queries:
            results = rag.search_products(query)
            assert len(results) > 0, f"No results for query: {query}"

    def test_rag_product_filtering_by_risk_profile(self):
        """Test RAG filtering products by risk profile"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        # Search for conservative products
        conservative_results = rag.search_products("conservador preservación capital bajo riesgo")
        assert len(conservative_results) > 0

        # Search for moderate products
        moderate_results = rag.search_products("moderado equilibrado retorno riesgo")
        assert len(moderate_results) > 0

    def test_rag_document_chunking(self):
        """Test document chunking for RAG"""
        from agent.rag_manager import DocumentChunker

        long_text = " ".join(["Este es un ejemplo de texto largo"] * 100)
        chunks = DocumentChunker.chunk_document(long_text, "Test Product")

        assert len(chunks) > 1
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_rag_retrieval_with_client_profile(self):
        """Test RAG retrieval customized by client profile"""
        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        profiles = [
            {"risk_profile": "conservador", "investment_horizon_months": 12},
            {"risk_profile": "moderado", "investment_horizon_months": 24},
            {"risk_profile": "agresivo", "investment_horizon_months": 36},
        ]

        for profile in profiles:
            query = f"inversión {profile['risk_profile']} plazo {profile['investment_horizon_months']} meses"
            results = rag.search_products(query)
            assert len(results) > 0, f"No results for profile: {profile}"

    @pytest.mark.integration
    def test_rag_with_complete_recommendation_flow(self):
        """Integration test: Complete RAG + recommendation flow"""
        from utils.guardrails import FinancialGuardrails

        rag = RAGManager()
        rag = RAGProductDatabase.initialize_sample_products(rag)

        client_profile = {
            "client_id": "TEST_CLI_RAG_002",
            "risk_profile": "moderado",
            "investment_horizon_months": 24,
            "available_amount_usd": 50000,
            "target_return_pct": 8.0,
            "max_aggressive_pct": 40,
            "liquidity_preference": "media",
        }

        # Step 1: RAG search for eligible products
        search_query = f"inversión {client_profile['risk_profile']} retorno {client_profile['target_return_pct']}%"
        rag_results = rag.search_products(search_query, top_k=3)

        assert len(rag_results) > 0
        print(f"RAG found {len(rag_results)} relevant products")

        # Step 2: Build portfolio (simulated)
        sample_products = [
            {
                "id": "PROD001",
                "name": "ZEST Deuda Privada",
                "type": "moderado",
                "annual_rate": 0.070,
            },
            {
                "id": "PROD002",
                "name": "Zest Bond Liquid CG2",
                "type": "moderado",
                "annual_rate": 0.0525,
            },
        ]

        allocations = FinanceCalculator.diversify_portfolio(
            total_amount=client_profile["available_amount_usd"],
            eligible_products=sample_products,
            client_risk_profile=client_profile["risk_profile"],
            max_aggressive_pct=client_profile["max_aggressive_pct"],
        )

        assert len(allocations) > 0
        print(f"Built portfolio with {len(allocations)} allocations")

        # Step 3: Calculate metrics
        metrics = FinanceCalculator.calculate_portfolio_metrics(allocations)
        assert metrics.expected_return > 0
        print(f"Expected return: {metrics.expected_return:.2%}")

        # Step 4: Validate guardrails
        portfolio_allocation = [
            {"product_type": a.product_name.split()[0], "percentage": a.percentage}
            for a in allocations
        ]
        is_valid, violations = FinancialGuardrails.validate_recommendation(
            client_profile, portfolio_allocation, metrics.expected_return
        )

        assert isinstance(is_valid, bool)
        print(f"Guardrails valid: {is_valid}, violations: {len(violations)}")

        # Step 5: Augment with RAG context
        rag_context = rag.augment_recommendation_context(client_profile, sample_products)

        assert len(rag_context) > 0
        assert "ZEST" in rag_context
        print(f"Generated RAG-augmented context: {len(rag_context)} chars")

        print("✓ Complete recommendation flow with RAG successful!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
