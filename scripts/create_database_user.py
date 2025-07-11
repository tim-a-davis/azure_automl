#!/usr/bin/env python
"""Create database user for service principal when using group-based admin."""

import os

import pyodbc
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")


def create_service_principal_user():
    """Create a database user for the service principal."""
    print("🔄 Creating database user for service principal...")
    print(f"Service Principal Client ID: {CLIENT_ID}")
    print(f"Database: {SQL_DATABASE}")

    try:
        # Get access token using your current credentials (as admin)
        credential = DefaultAzureCredential()
        token = credential.get_token("https://database.windows.net/.default")
        access_token = token.token

        print("✅ Got access token successfully")

        # Connect to database using your admin token
        connection_string = (
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{SQL_SERVER},1433;"
            f"Database={SQL_DATABASE};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )

        conn = pyodbc.connect(
            connection_string,
            attrs_before={
                1256: access_token  # SQL_COPT_SS_ACCESS_TOKEN
            },
        )

        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute(
            """
            SELECT COUNT(*) 
            FROM sys.database_principals 
            WHERE name = ? AND type IN ('E', 'X')
        """,
            CLIENT_ID,
        )

        user_exists = cursor.fetchone()[0] > 0

        if user_exists:
            print(f"✅ Database user for service principal {CLIENT_ID} already exists")
        else:
            # Create the database user
            print(f"🔄 Creating database user for service principal {CLIENT_ID}...")

            # Use the Client ID as the user name (this is the standard approach)
            create_user_sql = f"CREATE USER [{CLIENT_ID}] FROM EXTERNAL PROVIDER"
            cursor.execute(create_user_sql)

            print(f"✅ Created database user: {CLIENT_ID}")

        # Grant db_owner role (you can adjust permissions as needed)
        print("🔄 Granting db_owner role...")
        grant_role_sql = f"ALTER ROLE db_owner ADD MEMBER [{CLIENT_ID}]"
        cursor.execute(grant_role_sql)

        print(f"✅ Granted db_owner role to {CLIENT_ID}")

        # Verify the user was created successfully
        cursor.execute(
            """
            SELECT 
                name,
                CAST(sid AS UNIQUEIDENTIFIER) AS EntraID,
                CASE WHEN TYPE = 'E' THEN 'App/User' ELSE 'Group' END as user_type
            FROM sys.database_principals 
            WHERE name = ? AND type IN ('E', 'X')
        """,
            CLIENT_ID,
        )

        user_info = cursor.fetchone()
        if user_info:
            print("✅ User verification successful:")
            print(f"   Name: {user_info[0]}")
            print(f"   Entra ID: {user_info[1]}")
            print(f"   Type: {user_info[2]}")

        # Check role membership
        cursor.execute(
            """
            SELECT r.name 
            FROM sys.database_role_members rm
            JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
            JOIN sys.database_principals u ON rm.member_principal_id = u.principal_id
            WHERE u.name = ?
        """,
            CLIENT_ID,
        )

        roles = cursor.fetchall()
        print(f"✅ Role memberships: {', '.join([role[0] for role in roles])}")

        cursor.close()
        conn.close()

        print("\n🎉 SUCCESS! Your service principal now has database access.")
        print(
            "You can now test your API with the existing service principal authentication."
        )

        return True

    except Exception as e:
        print(f"❌ Failed to create database user: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Make sure you're connected as an admin user")
        print("2. Verify your service principal Client ID is correct")
        print("3. Check that the group admin is properly configured")
        return False


def main():
    """Main function."""
    print("🛠️  Azure SQL Database User Creation Script")
    print("=" * 50)
    print("This script creates a database user for your service principal")
    print("when using group-based Azure AD admin.")
    print("=" * 50)

    if not all([CLIENT_ID, SQL_SERVER, SQL_DATABASE]):
        print("❌ Missing required environment variables:")
        print("   AZURE_CLIENT_ID, SQL_SERVER, SQL_DATABASE")
        return

    success = create_service_principal_user()

    if success:
        print("\n🔥 Next steps:")
        print("1. Test your API connection: uv run python scripts/debug_connection.py")
        print("2. Start your API server: uv run python -m automlapi.runserver")
        print("3. Your service principal authentication should now work!")
    else:
        print("\n💡 If this didn't work:")
        print("1. Make sure you're authenticated as the Azure AD admin")
        print(
            "2. Try using Azure Data Studio or SSMS to connect and run the SQL manually"
        )
        print("3. Contact your Azure administrator for help")


if __name__ == "__main__":
    main()
