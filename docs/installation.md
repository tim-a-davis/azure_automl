# Installation Guide

This guide covers all dependencies, prerequisites, and installation steps for the Azure AutoML API.

## Dependencies Overview

To run the API you will need access to several Azure resources and some local tools:

- **Python 3.11** along with [uv](https://github.com/astral-sh/uv) for installing packages
- An **Azure subscription** containing an Azure Machine Learning workspace
- A **service principal** with permissions to the workspace (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`)
- An **Azure SQL Database** for persisting metadata (`SQL_SERVER`, `SQL_DATABASE`)
- A secret used to sign JSON Web Tokens (`JWT_SECRET`)
- [fastapi-mcp](https://pypi.org/project/fastapi-mcp/) to expose the API as an MCP server

## Prerequisites

### Install Python 3.11

Ensure you have Python 3.11 installed on your system. You can check your Python version:

```bash
python --version
```

If you need to install Python 3.11, visit [python.org](https://www.python.org/downloads/) or use your system's package manager.

### Install uv Package Manager

Install [uv](https://github.com/astral-sh/uv) for fast Python package management:

```bash
# macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

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

## Azure Resources Setup

### 1. Azure Machine Learning Workspace

You'll need an Azure ML workspace. If you don't have one:

1. Go to [Azure Portal](https://portal.azure.com)
2. Search for "Machine Learning" and create a new workspace
3. Note the following values for your `.env` file:
   - Subscription ID
   - Resource Group name
   - Workspace name

### 2. Service Principal

Create a service principal for API authentication:

```bash
# Using Azure CLI
az login
az ad sp create-for-rbac --name "AutoML-API-Service" --role Contributor --scopes /subscriptions/YOUR_SUBSCRIPTION_ID
```

This will output:
```json
{
  "appId": "your-client-id",
  "displayName": "AutoML-API-Service",
  "password": "your-client-secret",
  "tenant": "your-tenant-id"
}
```

Save these values for your environment configuration.

### 3. Azure SQL Database

You'll need an Azure SQL Database for storing metadata. See the [Database Setup Guide](database-setup.md) for detailed instructions.

## Installation Steps

### 1. Clone and Install Dependencies

```bash
# Clone the repository (if you haven't already)
git clone <repository-url>
cd azure_automl

# Install dependencies using uv
uv sync
```

This will create a virtual environment and install all required packages.

### 2. Environment Configuration

Create a `.env` file in the project root with your Azure and database settings:

```env
# Azure AD Configuration
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Azure ML Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_ML_WORKSPACE=your-workspace-name
AZURE_ML_RESOURCE_GROUP=your-resource-group-name

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-make-it-long-and-random

# Database Configuration
SQL_SERVER=your-sql-server.database.windows.net
SQL_DATABASE=your-database-name

# Environment setting
ENVIRONMENT=production  # Use 'local' for SQLite development
```

### 3. Initialize Database

Initialize the database tables:

```bash
# For production (Azure SQL Database)
uv run python scripts/create_tables.py

# For local development (SQLite)
export ENVIRONMENT=local
uv run python scripts/create_tables.py
```

### 4. Verify Installation

Test your installation:

```bash
# Test database connection
uv run python scripts/debug_connection.py

# Generate a test token
uv run python scripts/create_token.py testuser dev-tenant 24

# Start the API server
uv run python -m automlapi.runserver
```

The server should start on `http://localhost:8005`.

## Development Setup

For local development, you can use SQLite instead of Azure SQL Database:

### 1. Local Environment

Create a `.env.local` file:

```env
# Minimal configuration for local development
JWT_SECRET=your-local-development-secret
ENVIRONMENT=local

# Azure settings (can be dummy values for basic testing)
AZURE_TENANT_ID=dummy-tenant
AZURE_CLIENT_ID=dummy-client
AZURE_CLIENT_SECRET=dummy-secret
AZURE_SUBSCRIPTION_ID=dummy-subscription
AZURE_ML_WORKSPACE=dummy-workspace
AZURE_ML_RESOURCE_GROUP=dummy-resource-group
```

### 2. Initialize Local Database

```bash
export ENVIRONMENT=local
uv run python scripts/create_tables.py
```

This creates a local SQLite database file `automl_local.db`.

### 3. Run in Development Mode

```bash
# Start the server
uv run python -m automlapi.runserver

# Generate test tokens
uv run python scripts/create_token.py developer local-tenant 24
```

## Package Management with uv

The project uses `uv` for fast Python package management. Here are common commands:

```bash
# Install all dependencies
uv sync

# Add a new dependency
uv add package-name

# Add a development dependency
uv add --dev package-name

# Update dependencies
uv sync --upgrade

# Run a command in the virtual environment
uv run python script.py

# Activate the virtual environment manually
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows
```

## Container Deployment

For containerized deployment, use the provided Dockerfile:

```bash
# Build the container
docker build -t azure-automl-api .

# Run the container
docker run -p 8005:8005 --env-file .env azure-automl-api
```

## Troubleshooting Installation

### Common Issues

1. **ODBC Driver Issues on macOS**:
   ```bash
   # Reinstall ODBC driver
   brew uninstall msodbcsql18
   HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18
   ```

2. **Python Version Conflicts**:
   ```bash
   # Use specific Python version with uv
   uv python install 3.11
   uv sync --python 3.11
   ```

3. **Permission Issues**:
   ```bash
   # Ensure you have proper permissions for Azure resources
   az role assignment list --assignee YOUR_CLIENT_ID
   ```

4. **Network Connectivity**:
   ```bash
   # Test Azure connectivity
   ping your-sql-server.database.windows.net
   
   # Test Azure ML workspace access
   az ml workspace show --name YOUR_WORKSPACE --resource-group YOUR_RG
   ```

### Verification Steps

Run these commands to verify your installation:

```bash
# Check Python version
python --version

# Check uv installation
uv --version

# Check ODBC driver (macOS)
ls /opt/homebrew/lib/ | grep libmsodbcsql

# Test database connection
uv run python scripts/debug_connection.py

# Test token generation
uv run python scripts/create_token.py test user 1

# Start API server
uv run python -m automlapi.runserver
```

### Performance Optimization

For better performance:

1. **Use SSD storage** for SQLite database in development
2. **Configure connection pooling** for Azure SQL Database
3. **Use Azure regions** close to your location
4. **Enable caching** for frequently accessed data

### Security Considerations

1. **Never commit `.env` files** to version control
2. **Use Azure Key Vault** for production secrets
3. **Regularly rotate** service principal secrets
4. **Use least privilege** for Azure RBAC assignments
5. **Enable audit logging** for database access

## Next Steps

After installation:

1. Read the [Authentication Guide](authentication.md) to set up Azure AD integration
2. Follow the [Database Setup Guide](database-setup.md) for production database configuration
3. Check the [API Reference](api-reference.md) for endpoint documentation
4. See the [Testing Guide](testing.md) for testing approaches

## Getting Help

If you encounter issues:

1. Check the troubleshooting sections in each guide
2. Review Azure Portal logs and audit trails
3. Use the debug scripts in the `scripts/` directory
4. Check the [project issues](https://github.com/your-repo/issues) for known problems
