#!/usr/bin/env python3
"""
Seed script for FinAdvisor database
Initializes PostgreSQL with products, clients, and sample data from CSV files
"""

import os
import sys
import psycopg2
import csv
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_db_connection(host, database, user, password, port=5432):
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port
        )
        print(f"✅ Connected to PostgreSQL: {host}/{database}")
        return conn
    except psycopg2.Error as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)


def load_sql_file(filepath):
    """Load SQL script from file"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ SQL file not found: {filepath}")
        sys.exit(1)


def check_schema_exists(conn):
    """Check if schema already exists"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'products'")
        table_exists = cursor.fetchone()[0] > 0
        cursor.close()
        return table_exists
    except psycopg2.Error:
        return False


def execute_sql(conn, sql_script):
    """Execute SQL script (idempotent)"""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_script)
        conn.commit()
        cursor.close()
        print("✅ SQL schema created/updated")
    except psycopg2.Error as e:
        conn.rollback()
        # If error is about existing objects, it's OK - just warn
        if "already exists" in str(e):
            print(f"⚠️  Schema already exists (skipping): {e}")
        else:
            print(f"❌ SQL execution error: {e}")
            sys.exit(1)


def load_products_from_csv(filepath):
    """Load products from CSV file"""
    products = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                products.append({
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'annual_rate': float(row['annual_rate']),
                    'min_months': int(row['min_months']),
                    'max_months': int(row['max_months']),
                    'min_amount': float(row['min_amount']),
                    'liquidity': row['liquidity'],
                    'allows_buyback': row['allows_buyback'].lower() == 'true',
                    'withdrawal_window_months': int(row['withdrawal_window_months']),
                    'withdrawal_penalty_pct': float(row['withdrawal_penalty_pct'])
                })
        return products
    except FileNotFoundError:
        print(f"❌ CSV file not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)


def load_clients_from_csv(filepath):
    """Load clients from CSV file"""
    clients = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                clients.append({
                    'client_id': row['client_id'],
                    'name': row['name'],
                    'email': row['email'],
                    'risk_profile': row['risk_profile'],
                    'investment_horizon_months': int(row['investment_horizon_months']),
                    'available_amount_usd': float(row['available_amount_usd']),
                    'liquidity_preference': row['liquidity_preference'],
                    'target_return_pct': float(row['target_return_pct']),
                    'goals': row['goals']
                })
        return clients
    except FileNotFoundError:
        print(f"❌ CSV file not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)


def insert_products(conn, products):
    """Insert products into database"""
    cursor = conn.cursor()
    inserted = 0

    for product in products:
        try:
            cursor.execute("""
                INSERT INTO products
                (id, name, type, annual_rate, min_months, max_months, min_amount, liquidity, allows_buyback, withdrawal_window_months, withdrawal_penalty_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                product['id'],
                product['name'],
                product['type'],
                product['annual_rate'],
                product['min_months'],
                product['max_months'],
                product['min_amount'],
                product['liquidity'],
                product['allows_buyback'],
                product['withdrawal_window_months'],
                product['withdrawal_penalty_pct']
            ))
            if cursor.rowcount > 0:
                inserted += 1

        except psycopg2.Error as e:
            print(f"⚠️  Error inserting product {product['id']}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ Inserted {inserted} products")


def insert_clients(conn, clients):
    """Insert clients into database"""
    cursor = conn.cursor()
    inserted = 0

    for client in clients:
        try:
            cursor.execute("""
                INSERT INTO clients
                (client_id, name, email, risk_profile, investment_horizon_months, available_amount_usd, liquidity_preference, target_return_pct, goals)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (client_id) DO NOTHING
            """, (
                client['client_id'],
                client['name'],
                client['email'],
                client['risk_profile'],
                client['investment_horizon_months'],
                client['available_amount_usd'],
                client['liquidity_preference'],
                client['target_return_pct'],
                client['goals']
            ))
            if cursor.rowcount > 0:
                inserted += 1

        except psycopg2.Error as e:
            print(f"⚠️  Error inserting client {client['client_id']}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ Inserted {inserted} clients")


def load_portfolios_from_csv(filepath):
    """Load client portfolios from CSV file"""
    portfolios = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                portfolios.append({
                    'portfolio_id': row['portfolio_id'],
                    'client_id': row['client_id'],
                    'product_id': row['product_id'],
                    'allocation_amount': float(row['allocation_amount']),
                    'allocation_percentage': float(row['allocation_percentage']),
                    'purchase_date': row['purchase_date']
                })
        return portfolios
    except FileNotFoundError:
        print(f"❌ CSV file not found: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        sys.exit(1)


def insert_portfolios(conn, portfolios):
    """Insert client portfolios into database"""
    cursor = conn.cursor()
    inserted = 0

    # Clear existing portfolios
    cursor.execute("TRUNCATE TABLE client_portfolios CASCADE")

    for portfolio in portfolios:
        try:
            cursor.execute("""
                INSERT INTO client_portfolios
                (portfolio_id, client_id, product_id, allocation_amount, allocation_percentage, purchase_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                portfolio['portfolio_id'],
                portfolio['client_id'],
                portfolio['product_id'],
                portfolio['allocation_amount'],
                portfolio['allocation_percentage'],
                portfolio['purchase_date']
            ))
            if cursor.rowcount > 0:
                inserted += 1

        except psycopg2.Error as e:
            print(f"⚠️  Error inserting portfolio {portfolio['portfolio_id']}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ Inserted {inserted} portfolios")


def verify_data(conn):
    """Verify data was inserted correctly"""
    cursor = conn.cursor()

    # Count products
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    # Count clients
    cursor.execute("SELECT COUNT(*) FROM clients")
    client_count = cursor.fetchone()[0]

    # Count portfolios
    cursor.execute("SELECT COUNT(*) FROM client_portfolios")
    portfolio_count = cursor.fetchone()[0]

    cursor.close()

    print(f"\n📊 Database Status:")
    print(f"   Products: {product_count}")
    print(f"   Clients: {client_count}")
    print(f"   Portfolios: {portfolio_count}")

    return product_count > 0 and client_count > 0


def main():
    """Main seed script"""
    print("🌱 FinAdvisor Database Seed Script\n")

    # Get configuration from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'finadvisor')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'postgres')
    db_port = int(os.getenv('DB_PORT', '5432'))

    print(f"🔌 Connecting to {db_user}@{db_host}:{db_port}/{db_name}\n")

    # Connect to database
    conn = get_db_connection(db_host, db_name, db_user, db_password, db_port)

    try:
        # 0. Check if database already seeded
        if check_schema_exists(conn):
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            product_count = cursor.fetchone()[0]
            cursor.close()

            if product_count > 0:
                print("✅ Database already seeded (found {} products)".format(product_count))
                print("   Use 'make clean-volumes' to reset and reseed\n")
                verify_data(conn)
                return
            else:
                print("⚠️  Schema exists but no data found. Proceeding with seed...\n")

        # 1. Execute SQL schema
        print("📋 Creating schema...")
        sql_file = Path(__file__).parent.parent / "data" / "init_db.sql"
        sql_script = load_sql_file(sql_file)
        execute_sql(conn, sql_script)

        # 2. Load CSV data
        print("\n📂 Loading data files...")
        products_file = Path(__file__).parent.parent / "data" / "products.csv"
        clients_file = Path(__file__).parent.parent / "data" / "clients.csv"
        portfolios_file = Path(__file__).parent.parent / "data" / "portfolios.csv"

        products = load_products_from_csv(products_file)
        clients = load_clients_from_csv(clients_file)
        portfolios = load_portfolios_from_csv(portfolios_file)

        # 3. Insert data
        print("\n📥 Inserting data...")
        insert_products(conn, products)
        insert_clients(conn, clients)
        insert_portfolios(conn, portfolios)

        # 4. Verify
        print("\n✔️  Verifying...")
        if verify_data(conn):
            print("\n✅ Database seeding completed successfully!")
        else:
            print("\n⚠️  Warning: Some data may not have been inserted")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
