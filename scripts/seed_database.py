#!/usr/bin/env python3
"""
Seed script for FinAdvisor database
Initializes PostgreSQL with products, clients, and sample data
"""

import os
import sys
import psycopg2
import json
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


def execute_sql(conn, sql_script):
    """Execute SQL script"""
    try:
        cursor = conn.cursor()
        cursor.execute(sql_script)
        conn.commit()
        cursor.close()
        print("✅ SQL schema created/updated")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"❌ SQL execution error: {e}")
        sys.exit(1)


def load_json_data(filepath):
    """Load JSON data"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ JSON file not found: {filepath}")
        sys.exit(1)


def insert_products(conn, products_data):
    """Insert products into database"""
    cursor = conn.cursor()

    for product in products_data.get('products', []):
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

        except psycopg2.Error as e:
            print(f"⚠️  Error inserting product {product['id']}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ Inserted {len(products_data.get('products', []))} products")


def insert_clients(conn, clients_data):
    """Insert clients into database"""
    cursor = conn.cursor()

    for client in clients_data.get('clients', []):
        try:
            cursor.execute("""
                INSERT INTO clients
                (client_id, name, email, risk_profile, investment_horizon_months, available_amount_usd, liquidity_preference, target_return_pct, max_aggressive_pct, goals)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                client['max_aggressive_pct'],
                ', '.join(client['goals']) if client['goals'] else None
            ))

        except psycopg2.Error as e:
            print(f"⚠️  Error inserting client {client['client_id']}: {e}")

    conn.commit()
    cursor.close()
    print(f"✅ Inserted {len(clients_data.get('clients', []))} clients")


def verify_data(conn):
    """Verify data was inserted correctly"""
    cursor = conn.cursor()

    # Count products
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]

    # Count clients
    cursor.execute("SELECT COUNT(*) FROM clients")
    client_count = cursor.fetchone()[0]

    cursor.close()

    print(f"\n📊 Database Status:")
    print(f"   Products: {product_count}")
    print(f"   Clients: {client_count}")

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
        # 1. Execute SQL schema
        print("📋 Creating schema...")
        sql_file = Path(__file__).parent.parent / "data" / "init_db.sql"
        sql_script = load_sql_file(sql_file)
        execute_sql(conn, sql_script)

        # 2. Load JSON data
        print("\n📂 Loading data files...")
        products_file = Path(__file__).parent.parent / "data" / "products.json"
        clients_file = Path(__file__).parent.parent / "data" / "clients.json"

        products_data = load_json_data(products_file)
        clients_data = load_json_data(clients_file)

        # 3. Insert data
        print("\n📥 Inserting data...")
        insert_products(conn, products_data)
        insert_clients(conn, clients_data)

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
