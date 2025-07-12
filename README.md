# Azure AutoML API

This repository contains a thin REST layer built with **FastAPI** for interacting with Azure Machine Learning's AutoML capabilities. It is intended to sit between a web frontend and Azure, providing a unified set of HTTP endpoints to manage datasets, run experiments and deploy models.

The application exposes several routes that wrap the Azure ML SDK. Incoming requests are authenticated via JWT bearer tokens with support for both Azure AD integration and custom token generation. Azure credentials and database connection details are loaded from environment variables. Metadata for datasets, runs and models is stored in an Azure SQL Database through SQLAlchemy.

## Features

- Upload datasets to the workspace
- Launch AutoML experiments and monitor runs
- Browse registered models and endpoints
- Azure AD integration with token exchange
- Example background tasks for log streaming and dataset profiling

The service stores metadata in an Azure SQL Database using SQLAlchemy. Connection details and Azure credentials are supplied via environment variables or a `.env` file read by `Settings` in `automlapi.config`.

## Authentication Flow

The API supports two authentication modes:

### Production Mode: Azure AD Integration

For production deployments, the API integrates with Azure AD using the following flow:

1. **Frontend Authentication**: Your frontend application authenticates users with Azure AD using MSAL.js or similar:
   ```javascript
   const tokenRequest = {
     scopes: [`api://${CLIENT_ID}/access_as_user`],
   };
   const azureToken = await msalInstance.acquireTokenSilent(tokenRequest);
   ```

2. **Token Exchange**: The frontend exchanges the Azure AD token for an API token:
   ```javascript
   const response = await fetch('/auth/exchange', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({ azure_token: azureToken.accessToken })
   });
   const { access_token } = await response.json();
   ```

3. **API Access**: Use the returned access token for all API calls:
   ```javascript
   fetch('/datasets', {
     headers: { 'Authorization': `Bearer ${access_token}` }
   });
   ```

### Development Mode: Custom JWT Tokens

For testing and development, you can generate custom JWT tokens using the provided script:

```bash
uv run python scripts/create_token.py user123 my-tenant 24
```

This generates a token valid for 24 hours that can be used directly with the API.

## Dependencies

To run the API you will need access to several Azure resources and some local tools:

- **Python 3.11** along with [uv](https://github.com/astral-sh/uv) for installing packages.
- An **Azure subscription** containing an Azure Machine Learning workspace.
- A **service principal** with permissions to the workspace (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`).
- An **Azure SQL Database** for persisting metadata (`SQL_SERVER`, `SQL_DATABASE`). **Important**: You must be the Azure AD admin for the SQL Server and create a database user for the service principal to enable authentication.
- A secret used to sign JSON Web Tokens (`JWT_SECRET`).
- [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) to expose the API as an MCP server.

## Prerequisites

### macOS: Install ODBC Driver for SQL Server

If you're connecting to Azure SQL Database on macOS, you'll need to install the Microsoft ODBC Driver 18 for SQL Server:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18 mssql-tools18
```

### Other Operating Systems

For Windows and Linux installation instructions, see the [Microsoft documentation](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

## Quick start

1. Install dependencies using [uv](https://github.com/astral-sh/uv):

   ```bash
   uv sync
   ```

2. Provide the required Azure and database settings as environment variables. At a minimum the following values are expected:

   - `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
   - `AZURE_SUBSCRIPTION_ID`, `AZURE_ML_WORKSPACE`, `AZURE_ML_RESOURCE_GROUP`
   - `JWT_SECRET`

3. Initialize the database tables:

   ```bash
   uv run python scripts/create_tables.py
   ```

4. Launch the API server:

   ```bash
   uv run python -m automlapi.runserver
   ```

   The server listens on `http://0.0.0.0:8005`.

## Endpoints

The following routes are implemented by `automlapi.routes`:

### Authentication
- `POST /auth/exchange` – exchange an Azure AD token for an API access token
- `GET /auth/me` – get information about the current user

### Data Management
- `POST /datasets` – upload a file and register it as an Azure ML dataset.
- `GET  /datasets` – list available datasets.
- `POST /experiments` – start an experiment using the provided configuration.
- `GET  /experiments` – list experiments in the workspace.
- `GET  /runs` – list runs for the workspace.
- `GET  /models` – list registered models.
- `GET  /endpoints` – list deployment endpoints.

### User Management
- `POST /users` – create a user record.
- `GET  /users` – list users.

### RBAC
- `GET /rbac/assignments` – list Azure role assignments (requires Azure AD token)

WebSocket endpoints are available for run status and endpoint traffic streaming. See the source under `src/automlapi/routes` for details.

## Using as an MCP server

The API can be exposed as a [Model Context Protocol](https://tadata.com) (MCP) server by leveraging the [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) library. When the application starts it mounts an MCP server at the `/mcp` path, automatically converting available routes into MCP tools that language models can invoke.

With the package installed, no additional configuration is required. Simply start the server and query the MCP endpoint:

```bash
uv run python -m automlapi.runserver
# tools will be available under http://localhost:8005/mcp
```

Consult the [fastapi-mcp documentation](https://fastapi-mcp.tadata.com/) for advanced usage and authentication options.

## Setting up Azure AD Integration

To enable the full Azure AD authentication flow, you need to configure two app registrations in Microsoft Entra ID: one for your API service and one for your frontend application. This setup enables secure authentication and authorization between your frontend, API, and Azure services.

### Overview

The authentication flow works as follows:
1. User signs in to your frontend app using Azure AD
2. Frontend gets an access token with permission to call your API
3. Frontend exchanges this token with your API for an API-specific token
4. API uses this token to authenticate requests and make calls to Azure services on behalf of the user

### 1. Create API App Registration

First, create an app registration for your FastAPI service:

#### Step 1.1: Create the App Registration

1. Navigate to the [Azure Portal](https://portal.azure.com)
2. Go to **Microsoft Entra ID** (formerly Azure Active Directory)
3. In the left sidebar, click **App registrations**
4. Click **+ New registration**
5. Fill in the registration form:
   - **Name**: Enter a descriptive name like "AutoML API Service"
   - **Supported account types**: Select "Accounts in this organizational directory only" (single tenant)
   - **Redirect URI**: Leave blank for now (we'll configure this later)
6. Click **Register**

#### Step 1.2: Note Important IDs

After creation, you'll see the app registration overview page. **Copy and save these values** - you'll need them later:
- **Application (client) ID**: This is your `AZURE_CLIENT_ID`
- **Directory (tenant) ID**: This is your `AZURE_TENANT_ID`

#### Step 1.3: Create a Client Secret

1. In your app registration, click **Certificates & secrets** in the left sidebar
2. Click **+ New client secret**
3. Add a description like "API Secret"
4. Choose an expiration period (recommend 24 months maximum)
5. Click **Add**
6. **Important**: Copy the secret **Value** immediately - you won't be able to see it again. This is your `AZURE_CLIENT_SECRET`

#### Step 1.4: Configure API Permissions

1. Click **API permissions** in the left sidebar
2. Click **+ Add a permission**
3. Choose **Azure Service Management**
4. Select **Delegated permissions**
5. Check **user_impersonation**
6. Click **Add permissions**
7. **Important**: Click **Grant admin consent for [Your Organization]** and confirm
   - This allows your API to make calls to Azure services on behalf of users

#### Step 1.5: Expose an API

1. Click **Expose an API** in the left sidebar
2. Click **+ Add a scope**
3. For **Application ID URI**, accept the default `api://{client-id}` or customize it
4. Click **Save and continue**
5. Fill in the scope details:
   - **Scope name**: `access_as_user`
   - **Admin consent display name**: "Access AutoML API as user"
   - **Admin consent description**: "Allow the application to access the AutoML API on behalf of the signed-in user"
   - **User consent display name**: "Access AutoML API"
   - **User consent description**: "Allow the application to access the AutoML API on your behalf"
   - **State**: Enabled
6. Click **Add scope**

> **⚠️ Important**: After creating this API app registration, you must create a database user for it in your Azure SQL Database. Set yourself as the Azure AD admin for the SQL Server, then connect and run `CREATE USER [ServicePrincipalDisplayName] FROM EXTERNAL PROVIDER`. See the "Setting up Azure SQL Database" section below for detailed instructions.

### 2. Create Frontend App Registration

Now create a separate app registration for your frontend application:

#### Step 2.1: Create the Frontend App Registration

1. Still in **App registrations**, click **+ New registration**
2. Fill in the registration form:
   - **Name**: Enter a name like "AutoML Frontend"
   - **Supported account types**: Select "Accounts in this organizational directory only"
   - **Redirect URI**: 
     - Platform: **Single-page application (SPA)**
     - URI: Your frontend URL, e.g., `http://localhost:3000` for development
3. Click **Register**

#### Step 2.2: Note Frontend Client ID

Save the **Application (client) ID** for your frontend app - you'll need this in your frontend code.

#### Step 2.3: Configure Frontend API Permissions

1. Click **API permissions** in the left sidebar
2. Click **+ Add a permission**
3. Click **My APIs** tab
4. Select your API app registration (created in step 1)
5. Select **Delegated permissions**
6. Check **access_as_user**
7. Click **Add permissions**
8. Click **Grant admin consent for [Your Organization]** and confirm

#### Step 2.4: Configure Authentication

1. Click **Authentication** in the left sidebar
2. Under **Platform configurations**, you should see your SPA redirect URI
3. If you need to add more redirect URIs (e.g., for different environments), click **+ Add URI**
4. Under **Implicit grant and hybrid flows**, ensure both checkboxes are **unchecked** (modern SPAs use authorization code flow)

### 3. Assign Azure RBAC Roles

Your API needs permissions to access Azure Machine Learning and other Azure services:

#### Step 3.1: Navigate to Your Subscription

1. Go to **Subscriptions** in the Azure Portal
2. Select your subscription
3. Click **Access control (IAM)** in the left sidebar

#### Step 3.2: Add Role Assignment

1. Click **+ Add** → **Add role assignment**
2. In the **Role** tab, search for and select **Contributor** (or a more specific role like **Azure Machine Learning Data Scientist**)
3. Click **Next**
4. In the **Members** tab:
   - **Assign access to**: User, group, or service principal
   - Click **+ Select members**
   - Search for your API app registration name (e.g., "AutoML API Service")
   - Select it and click **Select**
5. Click **Review + assign**
6. Review and click **Assign**

### 4. Environment Configuration

Create a `.env` file in your project with the following variables:

```env
# Azure AD Configuration
AZURE_TENANT_ID=your-tenant-id-from-step-1.2
AZURE_CLIENT_ID=your-api-client-id-from-step-1.2
AZURE_CLIENT_SECRET=your-client-secret-from-step-1.3

# Azure ML Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_ML_WORKSPACE=your-ml-workspace-name
AZURE_ML_RESOURCE_GROUP=your-resource-group-name

# JWT Configuration
JWT_SECRET=your-random-jwt-secret-generate-a-long-random-string

# Database Configuration (if using SQL Database)
SQL_SERVER=your-sql-server.database.windows.net
SQL_DATABASE=your-database-name
```

## Setting up Azure SQL Database

The API uses Azure SQL Database to store metadata for datasets, experiments, models, and runs. The same service principal used for Azure ML authentication is also used for database authentication.

### 1. Create Azure SQL Database

If you don't already have an Azure SQL Database:

1. **Create Azure SQL Server**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Create a new **SQL Server** resource
   - Choose **Use only Azure Active Directory (Azure AD) authentication** (recommended)
   - Note the server name (e.g., `your-server.database.windows.net`)

2. **Create Database**:
   - In your SQL Server, create a new database
   - Choose appropriate pricing tier for your needs
   - Note the database name

### 2. Configure Azure AD Admin and Service Principal Database Access

**This is the critical step**: Set up Azure AD admin and create a database user for your service principal.

**Step 1: Set Azure AD Admin**
1. **Go to your SQL Server** (not the database) in Azure Portal
2. **Click "Azure Active Directory admin"** in the left sidebar under "Settings"
3. **Click "Set admin"**
4. **Search for your user account** (or a group you're in)
5. **Select your user** and click "Select"
6. **Click "Save"**

**Step 2: Create Database User for Service Principal**
1. **Connect to your database** as the Azure AD admin (using Azure Data Studio, SSMS, or Azure Portal Query Editor)
2. **Find your service principal's display name**:
   - Go to Azure Portal → Microsoft Entra ID → App registrations
   - Find your app registration using Client ID: `6e201af8-cd81-4240-8ec7-adef15cc9cd6`
   - Copy the "Display name" (e.g., "AutoML API Service")
3. **Run these SQL commands** (replace with your actual display name):
   ```sql
   CREATE USER [AutoML API Service] FROM EXTERNAL PROVIDER;
   ALTER ROLE db_owner ADD MEMBER [AutoML API Service];
   ```
4. **Verify the user was created**:
   ```sql
   SELECT name, type_desc FROM sys.database_principals 
   WHERE type IN ('E', 'X') AND name LIKE '%AutoML%';
   ```

**Important Notes**:
- You (the Azure AD admin) manage the SQL Server administration
- The service principal gets database-level access through explicit user creation
- This approach allows you to maintain admin control while giving the API programmatic access

### 3. Configure Firewall Rules

Ensure your SQL Server allows connections:

1. **Go to your SQL Server** in Azure Portal
2. **Click "Networking"** in the left sidebar
3. **Add firewall rules**:
   - **Allow Azure services**: Enable "Allow Azure services and resources to access this server"
   - **Add your IP**: If testing locally, add your current IP address
   - **Production**: Configure specific IP ranges for your deployment environment

### 4. Verify Connection

Test the database connection:

```bash
# Set environment to use Azure SQL Database
export ENVIRONMENT=production

# Test connection
uv run python scripts/debug_connection.py
```

You should see:
```
✅ Connection successful!
```

### 5. Database Authentication Details

The API uses **Azure AD Service Principal authentication** for the database:

- **Authentication Method**: `ActiveDirectoryServicePrincipal`
- **Username**: Your service principal's Client ID
- **Password**: Your service principal's Client Secret
- **Authority**: Your Azure AD Tenant ID

**Important**: The service principal must be added as an **Azure AD admin** for the SQL Server (not just the database). This is required for service principal authentication to work.

### 6. Azure AD Admin vs Database Users

Understanding the difference between Azure AD admin and database users:

**Azure AD Admin**:
- **One admin per SQL Server** (can be a user, group, service principal, or managed identity)
- **Server-level administration** privileges
- **Best practice**: Use your user account or an admin group for management

**Database Users**:
- **Created within each database** using `CREATE USER ... FROM EXTERNAL PROVIDER`
- **Database-level access** with specific permissions
- **For service principals**: Create explicit database users even if they're in admin groups
- **Grants programmatic access** to applications and APIs

**Recommended Setup**:
- **Admin**: Your user account (for management and control)
- **Service Principal**: Database user with specific permissions (for API access)

### 7. Local Development vs Production

The API automatically detects the environment:

- **Local Development** (`ENVIRONMENT=local`): Uses SQLite database (`automl_local.db`)
- **Production** (`ENVIRONMENT=production`): Uses Azure SQL Database

This allows you to develop locally without needing to set up Azure SQL Database for every developer.

### 8. Troubleshooting Database Connection

Common issues and solutions:

1. **"Login failed for user 'token-identified principal'"**:
   - ✅ **Solution**: Create a database user for your service principal:
     ```sql
     -- Connect as Azure AD admin, then run:
     CREATE USER [YourServicePrincipalDisplayName] FROM EXTERNAL PROVIDER;
     ALTER ROLE db_owner ADD MEMBER [YourServicePrincipalDisplayName];
     ```
   - ❌ **Not sufficient**: Just setting the service principal as SQL Server admin

2. **"Principal 'xxx' could not be found or this principal type is not supported"**:
   - Use the service principal's **display name** from the app registration, not the Client ID
   - Check the display name in Azure Portal → Microsoft Entra ID → App registrations

3. **"Login timeout expired"**:
   - Check firewall rules
   - Ensure "Allow Azure services" is enabled
   - Add your IP address to firewall rules

4. **"Cannot resolve server name"**:
   - Verify the SQL_SERVER name in your .env file
   - Ensure the server name includes `.database.windows.net`

5. **Connection works from portal but not from API**:
   - Verify the service principal has a database user created
   - Check that the database user has the correct permissions
   - Test with: `SELECT USER_NAME(), SYSTEM_USER` to see who you're connected as

6. **Find service principal display name**:
   ```bash
   # Use Azure CLI (after az login):
   az ad sp show --id YOUR_CLIENT_ID --query 'displayName' -o tsv
   
   # Or use the script:
   uv run python scripts/find_sp_name_simple.py
   ```

### 5. Frontend Integration

Here's how to integrate authentication in your frontend application:

#### Step 5.1: Install MSAL

```bash
npm install @azure/msal-browser
```

#### Step 5.2: Configure MSAL

```javascript
import { PublicClientApplication } from "@azure/msal-browser";

const msalConfig = {
  auth: {
    clientId: "your-frontend-client-id-from-step-2.2",
    authority: `https://login.microsoftonline.com/your-tenant-id`,
    redirectUri: window.location.origin
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false
  }
};

const msalInstance = new PublicClientApplication(msalConfig);
```

#### Step 5.3: Authentication Flow

```javascript
// Login user
async function login() {
  try {
    const loginRequest = {
      scopes: [`api://your-api-client-id/access_as_user`]
    };
    
    const response = await msalInstance.loginPopup(loginRequest);
    console.log("Login successful:", response);
    return response;
  } catch (error) {
    console.error("Login failed:", error);
    throw error;
  }
}

// Get API token
async function getApiToken() {
  try {
    const account = msalInstance.getActiveAccount();
    if (!account) {
      throw new Error("No active account");
    }

    const tokenRequest = {
      scopes: [`api://your-api-client-id/access_as_user`],
      account: account
    };

    const azureToken = await msalInstance.acquireTokenSilent(tokenRequest);
    
    // Exchange Azure token for API token
    const response = await fetch('/auth/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ azure_token: azureToken.accessToken })
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.status}`);
    }

    const { access_token } = await response.json();
    return access_token;
  } catch (error) {
    console.error("Token acquisition failed:", error);
    throw error;
  }
}

// Use API token for requests
async function callApi(endpoint, options = {}) {
  const token = await getApiToken();
  
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`API call failed: ${response.status}`);
  }
  
  return response.json();
}

// Example usage
async function loadDatasets() {
  try {
    const datasets = await callApi('/datasets');
    console.log("Datasets:", datasets);
    return datasets;
  } catch (error) {
    console.error("Failed to load datasets:", error);
  }
}
```

### 6. Testing Your Setup

1. **Start your API server**:
   ```bash
   uv run python -m automlapi.runserver
   ```

2. **Test the authentication endpoint**:
   - Navigate to your frontend application
   - Click login - you should see the Azure AD login page
   - After successful login, try calling an API endpoint
   - Check the browser network tab to see the token exchange happening

3. **Verify permissions**:
   - Your API should be able to access Azure ML resources
   - Check the Azure Portal activity logs to see if API calls are successful

### 7. Troubleshooting

**Common Issues:**

1. **"Invalid client" error**: Check that your client ID and tenant ID are correct
2. **"Invalid client secret" error**: Regenerate the client secret if it has expired
3. **"Insufficient permissions" error**: Ensure admin consent was granted for API permissions
4. **"Access denied" error**: Check that the API app registration has the correct RBAC roles assigned
5. **"Login failed for user 'token-identified principal'"**: The service principal must be added as an **Azure AD admin** for your Azure SQL Server (not just the database)
6. **CORS errors**: Ensure your API is configured to accept requests from your frontend domain

**Debugging Tips:**

- Use the browser developer tools to inspect token contents (decode JWT tokens at jwt.io)
- Check the Azure Portal audit logs under **Microsoft Entra ID** → **Audit logs**
- Enable detailed logging in your API to see authentication failures
- Test API endpoints directly using tools like Postman with manually generated tokens

### 8. Production Considerations

When deploying to production, consider these additional security measures:

#### Certificate-Based Authentication
Instead of client secrets, use certificates for enhanced security:

1. In your API app registration, go to **Certificates & secrets**
2. Click **Upload certificate** and upload your certificate file
3. Update your application to use certificate-based authentication

#### Environment-Specific Configuration
Set up separate app registrations for different environments:

- **Development**: `http://localhost:3000`
- **Staging**: `https://staging.yourapp.com`
- **Production**: `https://yourapp.com`

#### Security Best Practices

1. **Regular Secret Rotation**: Set up a process to rotate client secrets regularly
2. **Least Privilege**: Only grant the minimum required permissions
3. **Token Validation**: Implement proper token validation in your API
4. **Secure Storage**: Store sensitive configuration in Azure Key Vault
5. **Monitoring**: Set up alerts for authentication failures and unusual access patterns

#### Key Vault Integration

Store your secrets in Azure Key Vault:

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# In your config.py
def get_secret_from_keyvault(vault_url: str, secret_name: str) -> str:
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value

# Usage
JWT_SECRET = get_secret_from_keyvault(
    "https://your-keyvault.vault.azure.net/", 
    "jwt-secret"
)
```

This comprehensive guide should give you everything you need to set up Azure AD integration successfully. The key points are:

1. **Two app registrations**: One for your API, one for your frontend
2. **Proper scopes and permissions**: The frontend needs permission to call your API
3. **RBAC roles**: Your API needs permissions to access Azure resources
4. **Token exchange flow**: Frontend gets Azure token, exchanges it for API token
5. **Security considerations**: Use certificates, rotate secrets, monitor access

Follow each step carefully, and you'll have a secure authentication system integrated with Azure AD!

## Testing

Run unit tests with `uv run pytest`:

```bash
uv run pytest
```

## Testing the Backend API (Without Frontend)

You can fully test the backend API without setting up a frontend application. Here are several approaches:

### Method 1: Using Custom JWT Tokens (Recommended for Development)

The easiest way to test your API is using the built-in token generation script:

#### Step 1: Set up your environment

Create a `.env` file with minimal configuration:

```env
# Required for token generation
JWT_SECRET=your-super-secret-jwt-key-make-it-long-and-random

# Azure configuration (can be dummy values for basic testing)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id  
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_ML_WORKSPACE=your-workspace-name
AZURE_ML_RESOURCE_GROUP=your-resource-group

# Database (optional for basic testing)
SQL_SERVER=your-server.database.windows.net
SQL_DATABASE=your-database
```

#### Step 2: Generate a test token

```bash
# Generate a token valid for 24 hours
uv run python scripts/create_token.py testuser123 dev-tenant 24
```

This will output something like:
```
JWT Token for user 'testuser123' (tenant: 'dev-tenant', expires in 24 hours):
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlcjEyMyIsInRpZCI6ImRldi10ZW5hbnQiLCJpYXQiOjE3MDQ5NjAwMDAsImV4cCI6MTcwNTA0NjQwMH0.example_token

Use this token in your requests:
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Step 3: Start the API server

```bash
uv run python -m automlapi.runserver
```

#### Step 4: Test with curl

```bash
# Set your token as a variable (replace with your actual token)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Test authentication
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/auth/me

# List datasets
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/datasets

# List experiments
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/experiments

# List models
curl -H "Authorization: Bearer $TOKEN" http://localhost:8005/models

# Upload a dataset (create a test CSV first)
echo "col1,col2,col3" > test_data.csv
echo "1,2,3" >> test_data.csv
echo "4,5,6" >> test_data.csv

curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_data.csv" \
  -F "name=test_dataset" \
  -F "description=Test dataset for API testing" \
  http://localhost:8005/datasets
```

### Method 2: Using Postman

1. **Import API endpoints**: Create a new Postman collection
2. **Set up authentication**:
   - Go to the **Authorization** tab
   - Type: **Bearer Token**
   - Token: Paste your JWT token from the script
3. **Create requests**:

```http
GET http://localhost:8005/datasets
Authorization: Bearer YOUR_TOKEN_HERE

GET http://localhost:8005/auth/me
Authorization: Bearer YOUR_TOKEN_HERE

POST http://localhost:8005/datasets
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: multipart/form-data
Body: form-data
- file: [select your CSV file]
- name: "my_test_dataset"
- description: "Test dataset"
```

### Method 3: Python Testing Script

Create a comprehensive test script:

```python
#!/usr/bin/env python
"""Test the AutoML API with custom tokens."""

import requests
import json
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8005"
TOKEN = "your_jwt_token_here"  # Get this from create_token.py

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_auth():
    """Test authentication endpoint."""
    response = requests.get(f"{API_BASE_URL}/auth/me", headers=headers)
    print(f"Auth test: {response.status_code}")
    if response.status_code == 200:
        print(f"User info: {response.json()}")
    return response.status_code == 200

def test_list_datasets():
    """Test listing datasets."""
    response = requests.get(f"{API_BASE_URL}/datasets", headers=headers)
    print(f"List datasets: {response.status_code}")
    if response.status_code == 200:
        datasets = response.json()
        print(f"Found {len(datasets)} datasets")
        for dataset in datasets[:3]:  # Show first 3
            print(f"  - {dataset.get('name', 'Unknown')}")
    return response

def test_upload_dataset():
    """Test uploading a dataset."""
    # Create a test CSV
    test_csv = Path("/tmp/test_automl_data.csv")
    test_csv.write_text("feature1,feature2,target\n1,2,0\n3,4,1\n5,6,0\n")
    
    files = {
        'file': ('test_data.csv', open(test_csv, 'rb'), 'text/csv')
    }
    data = {
        'name': 'test_dataset_python',
        'description': 'Test dataset uploaded via Python script'
    }
    
    # Remove Content-Type header for multipart/form-data
    upload_headers = {"Authorization": f"Bearer {TOKEN}"}
    
    response = requests.post(
        f"{API_BASE_URL}/datasets", 
        headers=upload_headers,
        files=files,
        data=data
    )
    
    print(f"Upload dataset: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Upload successful: {response.json()}")
    else:
        print(f"Upload failed: {response.text}")
    
    # Cleanup
    test_csv.unlink()
    return response

def test_list_experiments():
    """Test listing experiments."""
    response = requests.get(f"{API_BASE_URL}/experiments", headers=headers)
    print(f"List experiments: {response.status_code}")
    if response.status_code == 200:
        experiments = response.json()
        print(f"Found {len(experiments)} experiments")
    return response

def test_list_models():
    """Test listing models."""
    response = requests.get(f"{API_BASE_URL}/models", headers=headers)
    print(f"List models: {response.status_code}")
    if response.status_code == 200:
        models = response.json()
        print(f"Found {len(models)} models")
    return response

def main():
    """Run all tests."""
    print("Testing AutoML API...")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Using token: {TOKEN[:20]}...")
    print("-" * 50)
    
    # Test authentication first
    if not test_auth():
        print("Authentication failed! Check your token and API server.")
        return
    
    print("-" * 50)
    
    # Test various endpoints
    test_list_datasets()
    print("-" * 20)
    test_upload_dataset()
    print("-" * 20)
    test_list_experiments()
    print("-" * 20)
    test_list_models()
    
    print("-" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    main()
```

Save this as `test_api.py` and run it:

```bash
# First generate a token
TOKEN=$(uv run python scripts/create_token.py testuser 2>&1 | grep "Bearer" | cut -d' ' -f3)

# Edit the script to use your token, then run
python test_api.py
```

### Method 4: Using HTTPie (Alternative to curl)

If you prefer HTTPie over curl:

```bash
# Install HTTPie
pip install httpie

# Set token
export TOKEN="your_jwt_token_here"

# Test endpoints
http GET localhost:8005/auth/me "Authorization:Bearer $TOKEN"
http GET localhost:8005/datasets "Authorization:Bearer $TOKEN"
http GET localhost:8005/experiments "Authorization:Bearer $TOKEN"

# Upload file
http --form POST localhost:8005/datasets \
  "Authorization:Bearer $TOKEN" \
  file@test_data.csv \
  name="test_dataset" \
  description="Test upload"
```

### Method 5: Interactive Testing with Python REPL

```python
import requests

# Set up session with auth
session = requests.Session()
session.headers.update({
    "Authorization": "Bearer YOUR_TOKEN_HERE"
})

# Test interactively
response = session.get("http://localhost:8005/auth/me")
print(response.json())

datasets = session.get("http://localhost:8005/datasets")
print(f"Datasets: {len(datasets.json())}")

# Upload a file
with open("test_data.csv", "rb") as f:
    files = {"file": ("test.csv", f, "text/csv")}
    data = {"name": "interactive_test", "description": "Test from REPL"}
    response = session.post("http://localhost:8005/datasets", files=files, data=data)
    print(f"Upload status: {response.status_code}")
```

### Quick Testing Checklist

Use this checklist to verify your API is working:

- [ ] **Environment**: `.env` file configured with `JWT_SECRET`
- [ ] **Database**: Tables created with `uv run python scripts/create_tables.py`
- [ ] **Server**: API running on `http://localhost:8005`
- [ ] **Token**: Generated with `uv run python scripts/create_token.py`
- [ ] **Auth**: `/auth/me` returns user info
- [ ] **Datasets**: Can list and upload datasets
- [ ] **Experiments**: Can list experiments
- [ ] **Models**: Can list models

### Troubleshooting API Testing

**Common Issues:**

1. **401 Unauthorized**: Check your token is valid and not expired
2. **500 Internal Server Error**: Check Azure credentials and database connection
3. **422 Validation Error**: Check request format and required fields
4. **Connection refused**: Ensure API server is running

**Debug Tips:**

```bash
# Check server logs
uv run python -m automlapi.runserver

# Validate your token
python -c "
import jwt
token = 'YOUR_TOKEN'
print(jwt.decode(token, options={'verify_signature': False}))
"

# Test basic connectivity
curl http://localhost:8005/docs  # Should show OpenAPI docs
```

This approach lets you fully test your API functionality without any frontend complexity!
