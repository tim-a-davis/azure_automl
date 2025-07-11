#!/usr/bin/env python
"""Test different authentication methods for Azure SQL Database when using group-based admin."""

import asyncio
import os
import sys

import pyodbc
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")


def test_service_principal_auth():
    """Test direct service principal authentication (may fail with group admin)."""
    print("🔄 Testing Service Principal Authentication...")

    connection_string = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{SQL_SERVER},1433;"
        f"Database={SQL_DATABASE};"
        f"Uid={CLIENT_ID};"
        f"Pwd={CLIENT_SECRET};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Connection Timeout=30;"
        f"Authentication=ActiveDirectoryServicePrincipal"
    )

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        print("✅ Service Principal Authentication: SUCCESS")
        print(f"   Test query result: {result[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print("❌ Service Principal Authentication: FAILED")
        print(f"   Error: {str(e)}")
        return False


async def test_token_auth():
    """Test access token authentication (should work with group admin)."""
    print("\n🔄 Testing Access Token Authentication...")

    try:
        # Get access token using service principal credentials
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
        )

        # Get token for SQL Database
        token = await credential.get_token("https://database.windows.net/.default")
        access_token = token.token

        print("✅ Access token obtained successfully")
        print(f"   Token expires at: {token.expires_on}")

        # Test database connection with access token
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{SQL_SERVER},1433;"
            f"Database={SQL_DATABASE};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        # Connect using access token
        conn = pyodbc.connect(
            connection_string,
            attrs_before={
                1256: access_token  # SQL_COPT_SS_ACCESS_TOKEN
            },
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user")
        result = cursor.fetchone()
        print("✅ Token Authentication: SUCCESS")
        print(f"   Test query result: {result[0]}")
        print(f"   Connected as user: {result[1]}")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print("❌ Token Authentication: FAILED")
        print(f"   Error: {str(e)}")
        return False


async def test_default_credential_auth():
    """Test DefaultAzureCredential authentication."""
    print("\n🔄 Testing DefaultAzureCredential Authentication...")

    try:
        # Use DefaultAzureCredential (will try various methods)
        credential = DefaultAzureCredential()

        # Get token for SQL Database
        token = await credential.get_token("https://database.windows.net/.default")
        access_token = token.token

        print("✅ DefaultAzureCredential token obtained successfully")

        # Test database connection with access token
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{SQL_SERVER},1433;"
            f"Database={SQL_DATABASE};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        # Connect using access token
        conn = pyodbc.connect(
            connection_string,
            attrs_before={
                1256: access_token  # SQL_COPT_SS_ACCESS_TOKEN
            },
        )

        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test, SYSTEM_USER as current_user")
        result = cursor.fetchone()
        print("✅ DefaultAzureCredential Authentication: SUCCESS")
        print(f"   Test query result: {result[0]}")
        print(f"   Connected as user: {result[1]}")
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print("❌ DefaultAzureCredential Authentication: FAILED")
        print(f"   Error: {str(e)}")
        return False


def check_group_membership():
    """Check if the service principal is properly added to the admin group."""
    print("\n🔄 Checking Group Membership...")
    print("To verify your service principal is in the admin group:")
    print("1. Go to Azure Portal → Azure Active Directory → Groups")
    print("2. Find your admin group")
    print("3. Check Members - ensure your service principal is listed")
    print(f"4. Your service principal Client ID: {CLIENT_ID}")


async def main():
    """Run all authentication tests."""
    print("🧪 Testing Azure SQL Database Authentication Methods")
    print("=" * 60)
    print(f"Server: {SQL_SERVER}")
    print(f"Database: {SQL_DATABASE}")
    print(f"Client ID: {CLIENT_ID}")
    print(f"Tenant ID: {TENANT_ID}")
    print("=" * 60)

    # Test methods in order of preference
    methods_tested = []

    # Method 1: Direct Service Principal (may fail with group admin)
    sp_success = test_service_principal_auth()
    methods_tested.append(("Service Principal", sp_success))

    # Method 2: Access Token (should work with group admin)
    token_success = await test_token_auth()
    methods_tested.append(("Access Token", token_success))

    # Method 3: DefaultAzureCredential (fallback)
    default_success = await test_default_credential_auth()
    methods_tested.append(("DefaultAzureCredential", default_success))

    # Show group membership check
    check_group_membership()

    # Summary
    print("\n" + "=" * 60)
    print("📊 AUTHENTICATION TEST SUMMARY")
    print("=" * 60)

    for method, success in methods_tested:
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{method:25} : {status}")

    print("\n🎯 RECOMMENDATIONS:")

    if sp_success:
        print("✅ Your service principal authentication works directly.")
        print("   No changes needed to your current setup.")
    elif token_success:
        print("✅ Access token authentication works!")
        print("   Update your database connection to use token-based auth.")
        print("   This is common when using group-based admin access.")
    elif default_success:
        print("✅ DefaultAzureCredential works!")
        print("   Consider switching to DefaultAzureCredential for authentication.")
    else:
        print("❌ All authentication methods failed.")
        print("   Check that:")
        print("   1. Your service principal is added to the admin group")
        print("   2. The group is set as Azure AD admin for the SQL Server")
        print("   3. Firewall rules allow your connection")
        print("   4. Your credentials are correct")


if __name__ == "__main__":
    # Check required environment variables
    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, SQL_SERVER, SQL_DATABASE]):
        print("❌ Missing required environment variables:")
        print("   AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
        print("   SQL_SERVER, SQL_DATABASE")
        sys.exit(1)

    # Run the tests
    asyncio.run(main())
