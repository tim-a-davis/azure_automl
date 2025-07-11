#!/usr/bin/env python
"""Simple script to show how to find and create your service principal user."""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("AZURE_CLIENT_ID")


def show_instructions():
    """Show instructions for finding the correct service principal name."""
    print("🔧 How to Find Your Service Principal Name for CREATE USER")
    print("=" * 60)

    print("\n📋 Method 1: Using Azure Portal")
    print("-" * 30)
    print("1. Go to Azure Portal → Microsoft Entra ID → App registrations")
    print("2. Find your app registration (search for your Client ID)")
    print(f"3. Your Client ID: {CLIENT_ID}")
    print("4. Copy the 'Display name' from the app registration")
    print("5. Use that display name in the CREATE USER command")

    print("\n📋 Method 2: Using Azure CLI")
    print("-" * 30)
    print("Run this command to get service principal info:")
    print(f"az ad sp show --id {CLIENT_ID}")
    print("Look for the 'displayName' field in the output")

    print("\n📋 Method 3: Try Common Patterns")
    print("-" * 30)
    print("Try these CREATE USER commands in order:")

    # Common patterns to try
    patterns = [
        "AutoML API Service",  # Likely display name
        "automl-api",  # Common naming pattern
        "automl-api-service",  # Another common pattern
        CLIENT_ID,  # Client ID itself
        f"AutoML-{CLIENT_ID[:8]}",  # Display name with partial ID
    ]

    for i, pattern in enumerate(patterns, 1):
        print(f"\n{i}. CREATE USER [{pattern}] FROM EXTERNAL PROVIDER;")
        print(f"   ALTER ROLE db_owner ADD MEMBER [{pattern}];")
        print(
            f"   -- Verify: SELECT name FROM sys.database_principals WHERE name = '{pattern}';"
        )

    print("\n🎯 Most Likely to Work:")
    print("The display name from your app registration (Method 1) is usually correct.")

    print("\n❌ If None Work:")
    print("The service principal might need to be created differently.")
    print("Try using Azure Data Studio or SSMS with these steps:")
    print("1. Connect as the Azure AD admin")
    print("2. Try creating with the app registration's Object ID instead")
    print("3. Check that the service principal exists in your tenant")


def check_azure_cli():
    """Check if Azure CLI is available and show command."""
    print("\n🔍 Azure CLI Quick Check")
    print("-" * 25)

    try:
        import subprocess

        result = subprocess.run(
            ["az", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("✅ Azure CLI is available")
            print("\nRun this command to get your service principal info:")
            print(f"az ad sp show --id {CLIENT_ID} --query 'displayName' -o tsv")
            print("\nOr for full details:")
            print(f"az ad sp show --id {CLIENT_ID}")
        else:
            print("❌ Azure CLI not working properly")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("❌ Azure CLI not found or not working")
        print(
            "You can install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        )


def main():
    """Main function."""
    if not CLIENT_ID:
        print("❌ Missing AZURE_CLIENT_ID in environment variables")
        return

    show_instructions()
    check_azure_cli()

    print("\n🔄 Next Steps:")
    print(
        "1. Find your service principal's display name using one of the methods above"
    )
    print("2. Try the CREATE USER command with that name")
    print("3. If successful, test your API connection")
    print("4. If it fails, try the next name pattern")


if __name__ == "__main__":
    main()
