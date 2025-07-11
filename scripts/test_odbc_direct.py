#!/usr/bin/env python3
"""Test ODBC connection directly"""

import os

import pyodbc

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


def test_odbc_connection():
    # Get values from environment
    server = os.getenv("SQL_SERVER", "automldbserver.database.windows.net")
    database = os.getenv("SQL_DATABASE", "automldb")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    print(f"Testing connection to: {server}")
    print(f"Database: {database}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * 10 if client_secret else 'NOT SET'}")

    # Use automldb as specified in Azure portal
    database = "automldb"
    print(f"Using database: {database}")

    # Connection string based on Azure portal
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{server},1433;"
        f"Database={database};"
        f"Uid={client_id};"
        f"Pwd={client_secret};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
        f"Authentication=ActiveDirectoryServicePrincipal"
    )

    print(f"\nConnection string: {conn_str}")

    try:
        print("\nAttempting connection...")
        conn = pyodbc.connect(conn_str)
        print("✅ Connection successful!")

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print(f"Query result: {result}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == "__main__":
    test_odbc_connection()
