#!/usr/bin/env python3
"""
Seed script for FinAdvisor
Initializes both RAG with product data from CSV files and PostgreSQL database
"""

import os
import sys
import csv
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agent.rag_manager import RAGManager, RAGProductDatabase
from backend.utils.config import get_config


def initialize_postgresql():
    """Initialize PostgreSQL database schema and sample data"""
    print("🗄️  Initializing PostgreSQL database...\n")

    config = get_config()
    db_config = config.get_db_config()

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_config['db_host'],
            port=db_config['db_port'],
            database=db_config['db_name'],
            user=db_config['db_user'],
            password=db_config['db_password']
        )
        cursor = conn.cursor()

        # Read and execute init SQL
        data_dir = Path(__file__).parent.parent / "data"
        init_sql_path = data_dir / "init_db.sql"

        if not init_sql_path.exists():
            print(f"❌ Error: {init_sql_path} not found!")
            return False

        with open(init_sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Execute SQL statements (split by semicolon)
        statements = sql_content.split(';')
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    cursor.execute(statement)
                except psycopg2.Error as e:
                    # Ignore "already exists" errors
                    if "already exists" not in str(e):
                        print(f"⚠️  Warning: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ PostgreSQL database initialized successfully!\n")
        return True

    except psycopg2.OperationalError as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        print(f"   Ensure PostgreSQL is running: make up")
        print(f"   Database config: {db_config['db_host']}:{db_config['db_port']}/{db_config['db_name']}\n")
        return False
    except Exception as e:
        print(f"❌ Error initializing database: {e}\n")
        return False


def load_products_from_csv(rag_manager, csv_path):
    """Load products from CSV file and add to RAG"""
    print(f"📖 Loading products from {csv_path}...\n")

    if not os.path.exists(csv_path):
        print(f"❌ Error: {csv_path} not found!")
        return False

    products_loaded = 0
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Create product document
                product_id = row.get('product_id')
                product_name = row.get('product_name')
                product_type = row.get('product_type')
                annual_return = row.get('annual_return_pct')
                volatility = row.get('annual_volatility_pct')
                liquidity_days = row.get('liquidity_days')
                liquidity_level = row.get('liquidity_level')
                description = row.get('description')

                # Create searchable document text
                doc_text = f"""
PRODUCTO: {product_name}
ID: {product_id}
TIPO: {product_type}
RETORNO ANUAL: {annual_return}%
VOLATILIDAD: {volatility}%
LIQUIDEZ: {liquidity_level} ({liquidity_days} días)
DESCRIPCIÓN: {description}
"""
                # Add to RAG
                rag_manager.add_document({
                    'product_id': product_id,
                    'product_name': product_name,
                    'product_type': product_type,
                    'annual_return_pct': float(annual_return),
                    'annual_volatility_pct': float(volatility),
                    'liquidity_days': int(liquidity_days),
                    'liquidity_level': liquidity_level,
                    'description': description,
                    'text': doc_text.strip()
                })

                products_loaded += 1
                print(f"  ✓ {product_name} ({annual_return}% retorno, {volatility}% volatilidad)")

        print(f"\n✅ Loaded {products_loaded} products\n")
        return True

    except Exception as e:
        print(f"❌ Error loading CSV: {e}\n")
        return False


def load_product_structure_from_csv(rag_manager, csv_path):
    """Load product structure (holdings) from CSV file"""
    print(f"📊 Loading product structure from {csv_path}...\n")

    if not os.path.exists(csv_path):
        print(f"❌ Error: {csv_path} not found!")
        return False

    holdings_by_product = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_id = row.get('product_id')
                product_name = row.get('product_name')
                asset_type = row.get('asset_type')
                allocation = row.get('allocation_percentage')
                ticker = row.get('ticker')
                company_name = row.get('company_name')
                sector = row.get('sector')
                risk_level = row.get('risk_level')

                # Group by product
                if product_id not in holdings_by_product:
                    holdings_by_product[product_id] = {
                        'product_name': product_name,
                        'holdings': []
                    }

                # Add holding
                holdings_by_product[product_id]['holdings'].append({
                    'asset_type': asset_type,
                    'allocation_percentage': float(allocation),
                    'ticker': ticker if ticker else 'N/A',
                    'company_name': company_name,
                    'sector': sector,
                    'risk_level': risk_level
                })

        # Create structure documents for RAG
        for product_id, data in holdings_by_product.items():
            holdings_text = f"""
COMPOSICIÓN DE {data['product_name']}:
"""
            for holding in data['holdings']:
                ticker_info = f" ({holding['ticker']})" if holding['ticker'] != 'N/A' else ""
                holdings_text += f"  • {holding['allocation_percentage']:.1f}% - {holding['company_name']}{ticker_info} [{holding['sector']}, riesgo: {holding['risk_level']}]\n"

            # Add to RAG
            rag_manager.add_document({
                'product_id': product_id,
                'product_name': data['product_name'],
                'document_type': 'holdings',
                'holdings': data['holdings'],
                'text': holdings_text.strip()
            })

            print(f"  ✓ {data['product_name']} - {len(data['holdings'])} componentes")

        print(f"\n✅ Loaded structure for {len(holdings_by_product)} products\n")
        return True

    except Exception as e:
        print(f"❌ Error loading structure CSV: {e}\n")
        return False


def check_database_seeded():
    """Check if database already has data"""
    try:
        config = get_config()
        db_config = config.get_db_config()

        conn = psycopg2.connect(
            host=db_config['db_host'],
            port=db_config['db_port'],
            database=db_config['db_name'],
            user=db_config['db_user'],
            password=db_config['db_password']
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count > 0
    except Exception:
        return False


def main():
    """Initialize FinAdvisor: PostgreSQL database and RAG"""
    print("🚀 FinAdvisor Data Initialization\n")
    print("=" * 50)

    # 0. Check if already seeded
    if check_database_seeded():
        print("✅ Database already seeded")
        print("   Use 'make clean-volumes' to reset and reseed\n")
        return

    # 1. Initialize PostgreSQL database
    if not initialize_postgresql():
        print("❌ Failed to initialize PostgreSQL. Stopping.\n")
        return

    # 2. Create RAG manager
    print("📚 Creating RAG Manager...")
    rag = RAGManager()

    # 3. RAG data is loaded automatically from PostgreSQL
    # No need for separate CSV files
    print("✅ RAG uses product data from PostgreSQL directly\n")

    # Verify
    print("=" * 50)
    print(f"✅ RAG initialized with {len(rag.storage.documents)} documentos\n")

    # Test search
    print("🔍 Testing RAG search:\n")

    test_queries = [
        "deuda privada retorno",
        "nota estructurada NASDAQ",
        "fondo conservador bajo riesgo",
        "renta variable tecnología",
        "liquidez alta bonos"
    ]

    for query in test_queries:
        results = rag.search_products(query, top_k=2)
        print(f"Query: '{query}'")
        if results:
            for result in results:
                print(f"  ✓ {result.get('product_name', 'N/A')} (score: {result.get('relevance_score', 0):.3f})")
        else:
            print(f"  ✗ No results found")
        print()

    print("=" * 50)
    print("✅ FinAdvisor initialization completed successfully!")
    print("\n📊 Data loaded:")
    print(f"  • PostgreSQL: Schema + 8 sample products + 4 sample clients")
    print(f"  • RAG: Product descriptions + component structure")
    print(f"\nData sources:")
    print(f"  • {products_csv}")
    print(f"  • {structure_csv}")
    print(f"  • {Path(__file__).parent.parent / 'data' / 'init_db.sql'}")


if __name__ == "__main__":
    main()
