# Authentication Guide

This guide covers the complete Azure AD authentication setup for the Azure AutoML API.

## Authentication Flow Overview

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

> **⚠️ Important**: After creating this API app registration, you must create a database user for it in your Azure SQL Database. Set yourself as the Azure AD admin for the SQL Server, then connect and run `CREATE USER [ServicePrincipalDisplayName] FROM EXTERNAL PROVIDER`. See the [Database Setup Guide](database-setup.md) for detailed instructions.

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

## Frontend Integration

Here's how to integrate authentication in your frontend application:

### Step 1: Install MSAL

```bash
npm install @azure/msal-browser
```

### Step 2: Configure MSAL

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

### Step 3: Authentication Flow

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

## Testing Your Setup

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

## Troubleshooting

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

## Production Considerations

When deploying to production, consider these additional security measures:

### Certificate-Based Authentication
Instead of client secrets, use certificates for enhanced security:

1. In your API app registration, go to **Certificates & secrets**
2. Click **Upload certificate** and upload your certificate file
3. Update your application to use certificate-based authentication

### Environment-Specific Configuration
Set up separate app registrations for different environments:

- **Development**: `http://localhost:3000`
- **Staging**: `https://staging.yourapp.com`
- **Production**: `https://yourapp.com`

### Security Best Practices

1. **Regular Secret Rotation**: Set up a process to rotate client secrets regularly
2. **Least Privilege**: Only grant the minimum required permissions
3. **Token Validation**: Implement proper token validation in your API
4. **Secure Storage**: Store sensitive configuration in Azure Key Vault
5. **Monitoring**: Set up alerts for authentication failures and unusual access patterns

### Key Vault Integration

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
