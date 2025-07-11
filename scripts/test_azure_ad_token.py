#!/usr/bin/env python3
"""Test Azure AD authentication for service principal"""

import os

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential

# Load environment variables
from dotenv import load_dotenv

load_dotenv()


def test_azure_ad_token():
    # Get values from environment
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")

    print("=== Testing Azure AD Service Principal Authentication ===")
    print(f"Tenant ID: {tenant_id}")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * 10 if client_secret else 'NOT SET'}")

    if not all([tenant_id, client_id, client_secret]):
        print("❌ Missing required environment variables")
        return False

    try:
        # Create credential
        credential = ClientSecretCredential(
            tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
        )

        # Test getting a token for Azure SQL Database
        print("\nTesting Azure SQL Database token...")
        token = credential.get_token("https://database.windows.net/.default")
        print("✅ Azure SQL Database token obtained successfully")
        print(f"Token expires at: {token.expires_on}")

        # Test getting a token for Azure Resource Manager
        print("\nTesting Azure Resource Manager token...")
        arm_token = credential.get_token("https://management.azure.com/.default")
        print("✅ Azure Resource Manager token obtained successfully")
        print(f"ARM Token expires at: {arm_token.expires_on}")

        return True

    except ClientAuthenticationError as e:
        print(f"❌ Azure AD authentication failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_azure_ad_token()

    if success:
        print("\n🎉 Azure AD Service Principal authentication is working!")
        print(
            "The issue is likely with SQL Server permissions, not the service principal itself."
        )
        print("\nNext steps:")
        print(
            "1. Verify the service principal was added as Azure AD admin for the SQL Server"
        )
        print("2. Check that the SQL Server has Azure AD authentication enabled")
        print("3. Ensure the service principal has proper permissions on the database")
    else:
        print("\n💥 Azure AD Service Principal authentication failed!")
        print("Please check your tenant ID, client ID, and client secret.")
