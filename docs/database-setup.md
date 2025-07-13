# Database Setup Guide

This guide covers setting up Azure SQL Database for the Azure AutoML API, including authentication configuration and troubleshooting.

## Overview

The API uses Azure SQL Database to store metadata for datasets, experiments, models, and runs. The same service principal used for Azure ML authentication is also used for database authentication.

## Create Azure SQL Database

If you don't already have an Azure SQL Database:

### 1. Create Azure SQL Server

1. Go to [Azure Portal](https://portal.azure.com)
2. Create a new **SQL Server** resource
3. Choose **Use only Azure Active Directory (Azure AD) authentication** (recommended)
4. Note the server name (e.g., `your-server.database.windows.net`)

### 2. Create Database

1. In your SQL Server, create a new database
2. Choose appropriate pricing tier for your needs
3. Note the database name

## Configure Azure AD Admin and Service Principal Database Access

**This is the critical step**: Set up Azure AD admin and create a database user for your service principal.

### Step 1: Set Azure AD Admin

1. **Go to your SQL Server** (not the database) in Azure Portal
2. **Click "Azure Active Directory admin"** in the left sidebar under "Settings"
3. **Click "Set admin"**
4. **Search for your user account** (or a group you're in)
5. **Select your user** and click "Select"
6. **Click "Save"**

### Step 2: Create Database User for Service Principal

1. **Connect to your database** as the Azure AD admin (using Azure Data Studio, SSMS, or Azure Portal Query Editor)
2. **Find your service principal's display name**:
   - Go to Azure Portal → Microsoft Entra ID → App registrations
   - Find your app registration using Client ID from your .env file
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

## Configure Firewall Rules

Ensure your SQL Server allows connections:

1. **Go to your SQL Server** in Azure Portal
2. **Click "Networking"** in the left sidebar
3. **Add firewall rules**:
   - **Allow Azure services**: Enable "Allow Azure services and resources to access this server"
   - **Add your IP**: If testing locally, add your current IP address
   - **Production**: Configure specific IP ranges for your deployment environment

## Environment Configuration

Update your `.env` file with database settings:

```env
# Database Configuration
SQL_SERVER=your-sql-server.database.windows.net
SQL_DATABASE=your-database-name

# Environment setting (determines which database to use)
ENVIRONMENT=production  # Use 'local' for SQLite development
```

## Verify Connection

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

## Database Authentication Details

The API uses **Azure AD Service Principal authentication** for the database:

- **Authentication Method**: `ActiveDirectoryServicePrincipal`
- **Username**: Your service principal's Client ID
- **Password**: Your service principal's Client Secret
- **Authority**: Your Azure AD Tenant ID

**Important**: The service principal must be added as a **database user** as described above. Simply setting it as the Azure AD admin for the SQL Server is not sufficient for programmatic access.

## Azure AD Admin vs Database Users

Understanding the difference between Azure AD admin and database users:

### Azure AD Admin

- **One admin per SQL Server** (can be a user, group, service principal, or managed identity)
- **Server-level administration** privileges
- **Best practice**: Use your user account or an admin group for management

### Database Users

- **Created within each database** using `CREATE USER ... FROM EXTERNAL PROVIDER`
- **Database-level access** with specific permissions
- **For service principals**: Create explicit database users even if they're in admin groups
- **Grants programmatic access** to applications and APIs

### Recommended Setup

- **Admin**: Your user account (for management and control)
- **Service Principal**: Database user with specific permissions (for API access)

## Local Development vs Production

The API automatically detects the environment:

- **Local Development** (`ENVIRONMENT=local`): Uses SQLite database (`automl_local.db`)
- **Production** (`ENVIRONMENT=production`): Uses Azure SQL Database

This allows you to develop locally without needing to set up Azure SQL Database for every developer.

## Initialize Database Tables

Once your connection is working, initialize the database tables:

```bash
# For production (Azure SQL Database)
export ENVIRONMENT=production
uv run python scripts/create_tables.py

# For local development (SQLite)
export ENVIRONMENT=local
uv run python scripts/create_tables.py
```

## Troubleshooting Database Connection

Common issues and solutions:

### 1. "Login failed for user 'token-identified principal'"

**Solution**: Create a database user for your service principal:
```sql
-- Connect as Azure AD admin, then run:
CREATE USER [YourServicePrincipalDisplayName] FROM EXTERNAL PROVIDER;
ALTER ROLE db_owner ADD MEMBER [YourServicePrincipalDisplayName];
```

**Not sufficient**: Just setting the service principal as SQL Server admin

### 2. "Principal 'xxx' could not be found or this principal type is not supported"

- Use the service principal's **display name** from the app registration, not the Client ID
- Check the display name in Azure Portal → Microsoft Entra ID → App registrations

### 3. "Login timeout expired"

- Check firewall rules
- Ensure "Allow Azure services" is enabled
- Add your IP address to firewall rules

### 4. "Cannot resolve server name"

- Verify the SQL_SERVER name in your .env file
- Ensure the server name includes `.database.windows.net`

### 5. Connection works from portal but not from API

- Verify the service principal has a database user created
- Check that the database user has the correct permissions
- Test with: `SELECT USER_NAME(), SYSTEM_USER` to see who you're connected as

### 6. Find service principal display name

```bash
# Use Azure CLI (after az login):
az ad sp show --id YOUR_CLIENT_ID --query 'displayName' -o tsv

# Or use the script:
uv run python scripts/find_sp_name_simple.py
```

## Database Migration

If you need to migrate from SQLite to Azure SQL Database:

```bash
# Use the migration script
uv run python scripts/migrate_to_azure_sql.py
```

This script will:
1. Export data from your local SQLite database
2. Create tables in Azure SQL Database
3. Import the data to Azure SQL Database

## Security Best Practices

1. **Use Azure AD authentication** instead of SQL authentication
2. **Restrict firewall rules** to only necessary IP ranges
3. **Regular access reviews** of database users and permissions
4. **Monitor database access** through Azure SQL Database audit logs
5. **Use least privilege** - don't give db_owner unless necessary

## Connection String Details

The API constructs connection strings automatically based on your environment:

### Production (Azure SQL Database)
```
mssql+pyodbc:///?odbc_connect=DRIVER={ODBC Driver 18 for SQL Server};SERVER=server.database.windows.net;DATABASE=database;Authentication=ActiveDirectoryServicePrincipal;UID=client_id;PWD=client_secret;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

### Local Development (SQLite)
```
sqlite:///automl_local.db
```

The API automatically selects the appropriate connection string based on the `ENVIRONMENT` variable.

## Database Schema

The database includes tables for:

- **Users**: User accounts and roles
- **Datasets**: Dataset metadata and storage references
- **Experiments**: AutoML experiment configurations
- **Runs**: Experiment run status and results
- **Models**: Registered model information
- **Endpoints**: Deployment endpoint configurations

Tables are automatically created using Alembic migrations when you run `create_tables.py`.

## Backup and Recovery

For production deployments:

1. **Enable automated backups** in Azure SQL Database settings
2. **Configure point-in-time restore** settings
3. **Test backup restore procedures** regularly
4. **Consider geo-replication** for disaster recovery

## Performance Considerations

For optimal performance:

1. **Choose appropriate service tier** based on workload
2. **Monitor DTU/vCore usage** in Azure Portal
3. **Add indexes** for frequently queried columns
4. **Use connection pooling** in the application
5. **Monitor slow queries** and optimize as needed

## Cost Optimization

To manage costs:

1. **Right-size your database tier** based on actual usage
2. **Use reserved capacity** for predictable workloads
3. **Consider serverless** for intermittent usage patterns
4. **Monitor costs** in Azure Cost Management
5. **Clean up old data** periodically to manage storage costs
