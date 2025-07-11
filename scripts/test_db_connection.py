#!/usr/bin/env python3
"""
Debug script to test Azure SQL Database connection with different authentication methods.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automlapi.config import settings


def test_connection():
    """Test the database connection and print connection details."""

    print("=== Azure SQL Database Connection Test ===")
    print(f"Environment: {settings.environment}")
    print(f"SQL Server: {settings.sql_server}")
    print(f"SQL Database: {settings.sql_database}")
    print(f"SQL Port: {settings.sql_port}")
    print(f"Azure Tenant ID: {settings.azure_tenant_id}")
    print(f"Azure Client ID: {settings.azure_client_id}")
    print(
        f"Azure Client Secret: {'*' * len(settings.azure_client_secret) if settings.azure_client_secret else 'Not set'}"
    )
    print()

    # Test database URL construction
    try:
        db_url = settings.database_url
        print(f"Database URL: {db_url}")
        print()
    except Exception as e:
        print(f"Error constructing database URL: {e}")
        return

    # Test connection using SQLAlchemy
    try:
        from sqlalchemy import create_engine, text

        print("Testing SQLAlchemy connection...")
        engine = create_engine(db_url, echo=True)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            print(f"Connection successful! Test result: {result.fetchone()}")

    except Exception as e:
        print(f"SQLAlchemy connection failed: {e}")
        print()

        # Try to get more details about the error
        if "Login failed" in str(e):
            print("AUTHENTICATION ERROR:")
            print("- The service principal may not have access to the database")
            print("- The database server may not exist")
            print("- The database may not exist")
            print("- The connection string may be incorrect")
            print()
            print("TROUBLESHOOTING STEPS:")
            print("1. Verify the Azure SQL Database server exists:")
            print(f"   Server: {settings.sql_server}")
            print("2. Verify the database exists:")
            print(f"   Database: {settings.sql_database}")
            print("3. Check if the service principal has access:")
            print(f"   Client ID: {settings.azure_client_id}")
            print("4. Verify the service principal has the following roles:")
            print("   - SQL DB Contributor or higher")
            print("   - Access to the specific database")
            print()
            print("5. Try using SQL authentication instead:")
            print("   Set SQL_USERNAME and SQL_PASSWORD in .env file")
            print("   Set ENVIRONMENT=local")


if __name__ == "__main__":
    test_connection()
