#!/usr/bin/env python3
"""Test connection to master database first"""

import os

import pyodbc

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


def test_master_connection():
    # Get values from environment
    server = os.getenv("SQL_SERVER", "automldbserver.database.windows.net")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    print(f"Testing connection to master database on: {server}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * 10 if client_secret else 'NOT SET'}")

    # Connection string for master database
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{server},1433;"
        f"Database=master;"
        f"Uid={client_id};"
        f"Pwd={client_secret};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
        f"Authentication=ActiveDirectoryServicePrincipal"
    )

    print(f"\nConnection string: {conn_str}")

    try:
        print("\nAttempting connection to master database...")
        conn = pyodbc.connect(conn_str)
        print("✅ Connection to master successful!")

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"Query result: {result}")

        # Try to list databases
        cursor.execute(
            "SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')"
        )
        databases = cursor.fetchall()
        print(f"Available databases: {[db[0] for db in databases]}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection to master failed: {e}")
        return False


def test_automldb_connection():
    # Get values from environment
    server = os.getenv("SQL_SERVER", "automldbserver.database.windows.net")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    print(f"\nTesting connection to automldb database on: {server}")

    # Connection string for automldb database
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{server},1433;"
        f"Database=automldb;"
        f"Uid={client_id};"
        f"Pwd={client_secret};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
        f"Authentication=ActiveDirectoryServicePrincipal"
    )

    try:
        print("Attempting connection to automldb database...")
        conn = pyodbc.connect(conn_str)
        print("✅ Connection to automldb successful!")

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"Query result: {result}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection to automldb failed: {e}")
        return False


if __name__ == "__main__":
    print("=== Testing Azure SQL Database Connection ===")

    # Test master database first
    master_success = test_master_connection()

    # Test automldb database
    automldb_success = test_automldb_connection()

    print("\n=== Results ===")
    print(f"Master database: {'✅ SUCCESS' if master_success else '❌ FAILED'}")
    print(f"AutoMLDB database: {'✅ SUCCESS' if automldb_success else '❌ FAILED'}")
