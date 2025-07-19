#!/usr/bin/env python3
"""
Simplified user authentication test using device code flow.
This avoids redirect URI issues by using device code instead of browser redirect.
"""

import os
import sys
from datetime import datetime

import jwt
import requests
from azure.identity import DeviceCodeCredential
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.insert(0, "src")

# Load environment variables
load_dotenv()


def device_code_user_auth():
    """Use device code flow for user authentication - no redirect URI needed."""
    print("Device Code User Authentication Test")
    print("=" * 40)

    # Get Azure credentials from environment
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")

    if not all([tenant_id, client_id]):
        print("❌ Missing required Azure credentials in environment variables")
        return

    print(f"Tenant ID: {tenant_id}")
    print(f"Client ID: {client_id}")
    print("\n🔑 Starting device code authentication flow...")
    print("This will give you a code to enter in a browser with YOUR user account")
    print("(Not the service principal - this is your actual user login)")

    try:
        # Device code flow doesn't need redirect URI configuration
        credential = DeviceCodeCredential(
            tenant_id=tenant_id,
            client_id=client_id,
        )

        # First try our custom API scope
        print("\n📱 Attempting to get token for our API...")
        scope = f"api://{client_id}/access_as_user"
        print(f"Requesting scope: {scope}")

        try:
            token_response = credential.get_token(scope)
            user_token = token_response.token

            print("✅ User token obtained successfully!")
            print(
                f"Token expires at: {datetime.fromtimestamp(token_response.expires_on)}"
            )

            # Analyze the token
            decoded = jwt.decode(user_token, options={"verify_signature": False})
            print("\n📋 User Token Claims:")
            for key, value in decoded.items():
                if key in [
                    "aud",
                    "iss",
                    "sub",
                    "scp",
                    "roles",
                    "appid",
                    "tid",
                    "oid",
                    "upn",
                    "name",
                ]:
                    print(f"  {key}: {value}")

            # Test with our API
            print("\n🧪 Testing user token with API...")
            response = requests.post(
                "http://localhost:8005/auth/exchange",
                json={"azure_token": user_token},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                print("✅ Token exchange successful!")
                token_data = response.json()
                api_jwt = token_data["access_token"]

                print(f"   API JWT obtained for user: {token_data.get('user_id')}")

                # Test API endpoints
                print("\n🧪 Testing API endpoints...")
                headers = {"Authorization": f"Bearer {api_jwt}"}

                # Test user info
                user_info_response = requests.get(
                    "http://localhost:8005/auth/me", headers=headers
                )
                if user_info_response.status_code == 200:
                    user_info = user_info_response.json()
                    print("✅ User info endpoint working:")
                    print(
                        f"   User: {user_info.get('name', 'Unknown')} ({user_info.get('upn', 'No UPN')})"
                    )
                    print(f"   User ID: {user_info.get('user_id')}")
                    print(f"   Tenant ID: {user_info.get('tenant_id')}")

                # Test RBAC (uses original Azure token, not API JWT)
                rbac_headers = {"Authorization": f"Bearer {user_token}"}
                rbac_response = requests.get(
                    "http://localhost:8005/rbac/assignments", headers=rbac_headers
                )
                if rbac_response.status_code == 200:
                    assignments = rbac_response.json()
                    print(assignments)
                    print(
                        f"✅ RBAC endpoint working: {len(assignments)} assignments found"
                    )
                else:
                    print(f"❌ RBAC endpoint failed: {rbac_response.status_code}")
                    print(f"   Error: {rbac_response.text}")
                    print(
                        "   Note: RBAC endpoint expects original Azure token, not API JWT"
                    )

                print("\n🎉 User authentication flow completed successfully!")
                print("\n🔑 Your user JWT token for testing:")
                print(f"Authorization: Bearer {api_jwt}")

            else:
                print(f"❌ Token exchange failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except Exception as api_error:
            print(f"❌ Failed to get token for our API: {api_error}")

            # Try with Microsoft Graph as fallback to verify user login works
            print("\n🔄 Trying Microsoft Graph scope as fallback...")
            try:
                graph_token_response = credential.get_token(
                    "https://graph.microsoft.com/User.Read"
                )
                graph_token = graph_token_response.token

                print("✅ Microsoft Graph token obtained!")

                # Decode to show user info
                decoded = jwt.decode(graph_token, options={"verify_signature": False})
                print(
                    f"   Logged in as: {decoded.get('name', 'Unknown')} ({decoded.get('upn', 'No UPN')})"
                )
                print(f"   User ID: {decoded.get('oid', 'Unknown')}")

                print("\n📝 This confirms user authentication works!")
                print("   The issue is with the custom API scope configuration.")
                print("   Please check Azure Portal app registration settings.")

            except Exception as graph_error:
                print(f"❌ Graph token also failed: {graph_error}")

    except Exception as e:
        print(f"❌ Authentication error: {e}")

    print("\n" + "=" * 60)
    print("📝 TROUBLESHOOTING CHECKLIST:")
    print("=" * 60)
    print("1. ✅ Add redirect URI: http://localhost:8400")
    print("   - Azure Portal > App Registrations > Your App > Authentication")
    print("   - Add platform > Single-page application")
    print("   - Or use Public client/native platform")

    print("\n2. ✅ Enable public client flows:")
    print("   - Azure Portal > App Registrations > Your App > Authentication")
    print("   - Advanced settings > Allow public client flows: YES")

    print("\n3. ✅ Verify API scope exists:")
    print("   - Azure Portal > App Registrations > Your App > Expose an API")
    print("   - Should have 'access_as_user' scope")

    print("\n4. ✅ Grant API permissions:")
    print("   - Azure Portal > App Registrations > Your App > API permissions")
    print("   - Should have permission to your own API")
    print("   - Click 'Grant admin consent'")


if __name__ == "__main__":
    device_code_user_auth()
