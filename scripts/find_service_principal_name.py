#!/usr/bin/env python
"""Find the correct name for your service principal to use in CREATE USER."""

import os

from azure.identity import ClientSecretCredential
from dotenv import load_dotenv
from msgraph import GraphServiceClient

# Load environment variables
load_dotenv()

# Configuration
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")


async def get_service_principal_info():
    """Get detailed information about the service principal."""
    print("🔍 Looking up service principal information...")

    try:
        # Use client credentials to get service principal info
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
        )

        # Get an access token for Microsoft Graph
        token = await credential.get_token("https://graph.microsoft.com/.default")

        # Create Graph client
        graph_client = GraphServiceClient(credentials=credential)

        # Get service principal by client ID
        service_principals = await graph_client.service_principals.get(
            request_configuration=lambda req_config: setattr(
                req_config.query_parameters, "filter", f"appId eq '{CLIENT_ID}'"
            )
        )

        if service_principals and service_principals.value:
            sp = service_principals.value[0]

            print("✅ Service Principal found!")
            print(f"   Display Name: {sp.display_name}")
            print(f"   Object ID: {sp.id}")
            print(f"   App ID (Client ID): {sp.app_id}")
            print(f"   Service Principal Type: {sp.service_principal_type}")

            # Try different name formats for CREATE USER
            possible_names = [
                sp.display_name,  # Display name
                sp.app_id,  # Client ID / App ID
                sp.id,  # Object ID
                f"{sp.display_name}@{TENANT_ID}",  # With tenant
            ]

            print("\n🎯 Try these names in CREATE USER command:")
            for i, name in enumerate(possible_names, 1):
                print(f"   {i}. CREATE USER [{name}] FROM EXTERNAL PROVIDER")

            return possible_names

        else:
            print("❌ Service principal not found!")
            print("   Check that your CLIENT_ID is correct")
            return None

    except Exception as e:
        print(f"❌ Error looking up service principal: {str(e)}")
        return None


async def check_azure_ad_apps():
    """Check app registrations to get the correct name."""
    print("\n🔍 Checking app registrations...")

    try:
        credential = ClientSecretCredential(
            tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
        )

        graph_client = GraphServiceClient(credentials=credential)

        # Get application by client ID
        applications = await graph_client.applications.get(
            request_configuration=lambda req_config: setattr(
                req_config.query_parameters, "filter", f"appId eq '{CLIENT_ID}'"
            )
        )

        if applications and applications.value:
            app = applications.value[0]

            print("✅ App Registration found!")
            print(f"   Display Name: {app.display_name}")
            print(f"   App ID: {app.app_id}")
            print(f"   Object ID: {app.id}")

            return app.display_name

        else:
            print("❌ App registration not found!")
            return None

    except Exception as e:
        print(f"❌ Error checking app registration: {str(e)}")
        return None


def generate_sql_commands(names):
    """Generate SQL commands to try."""
    if not names:
        return

    print("\n📝 SQL Commands to try (in order of likelihood):")
    print("=" * 50)

    for i, name in enumerate(names, 1):
        print(f"\n-- Option {i}: Using {name}")
        print(f"CREATE USER [{name}] FROM EXTERNAL PROVIDER;")
        print(f"ALTER ROLE db_owner ADD MEMBER [{name}];")
        print("-- Check if it worked:")
        print(
            f"SELECT name, type_desc FROM sys.database_principals WHERE name = '{name}';"
        )


async def main():
    """Main function."""
    print("🔧 Service Principal Name Finder")
    print("=" * 40)
    print("This script helps find the correct name for your service principal")
    print("to use in CREATE USER commands.")
    print("=" * 40)

    if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET]):
        print("❌ Missing required environment variables:")
        print("   AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET")
        return

    # Get service principal info
    sp_names = await get_service_principal_info()

    # Get app registration info
    app_name = await check_azure_ad_apps()

    # Combine all possible names
    all_names = []
    if sp_names:
        all_names.extend(sp_names)
    if app_name and app_name not in all_names:
        all_names.append(app_name)

    # Generate SQL commands
    generate_sql_commands(all_names)

    print("\n💡 Tips:")
    print("1. Try each SQL command in order until one works")
    print("2. The display name is usually the most reliable")
    print("3. If none work, the service principal might not be visible to your tenant")
    print(
        "4. You can also try using the service principal's Object ID from Azure Portal"
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
