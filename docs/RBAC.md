# Role-Based Access Control (RBAC) in AutoML API

This document describes the role-based access control system implemented in the AutoML API.

## Overview

The AutoML API now includes a comprehensive RBAC system with three hierarchical user roles:

- **USER**: Basic access level, can read data and create experiments/runs
- **MAINTAINER**: Intermediate access level, can do everything a USER can do plus delete operations
- **ADMIN**: Full access level, can do everything plus manage users and roles

## User Roles

### USER Role
**Permissions:**
- Read access to all resources (datasets, experiments, runs, models, endpoints)
- Create new experiments and runs
- Upload and create datasets
- View their own user information

**Restrictions:**
- Cannot delete any resources
- Cannot manage users or roles

### MAINTAINER Role
**Permissions:**
- All USER permissions
- Delete datasets, experiments, runs, models, and endpoints
- Full management of experimental data

**Restrictions:**
- Cannot manage users or roles

### ADMIN Role
**Permissions:**
- All MAINTAINER permissions
- Create and delete users
- Create and delete roles
- Full system administration

## API Endpoints and Required Roles

### User and Role Management (ADMIN only)
- `POST /users` - Create new users
- `DELETE /users/{user_id}` - Delete users
- `POST /roles` - Create new roles
- `DELETE /roles/{role_id}` - Delete roles

### Data Management (MAINTAINER+ for deletes)
- `DELETE /datasets/{dataset_id}` - Delete datasets (MAINTAINER/ADMIN)
- `DELETE /experiments/{experiment_id}` - Delete experiments (MAINTAINER/ADMIN)
- `DELETE /runs/{run_id}` - Delete runs (MAINTAINER/ADMIN)
- `DELETE /models/{model_id}` - Delete models (MAINTAINER/ADMIN)
- `DELETE /endpoints/{endpoint_id}` - Delete endpoints (MAINTAINER/ADMIN)

### Read Operations (All authenticated users)
All GET endpoints are accessible by any authenticated user with any role.

### Create Operations (All authenticated users)
Most create operations (POST) are accessible by any authenticated user, except for user and role management.

## Implementation Details

### Authentication Flow
1. User provides JWT token in Authorization header
2. Token is validated and decoded to extract user_id
3. User record is looked up in database to get role information
4. Role-based permissions are checked before allowing access to protected endpoints

### Role Hierarchy
The system implements a hierarchical role model where higher-level roles inherit all permissions from lower-level roles:

```
ADMIN (level 3)
  ├── All MAINTAINER permissions
  ├── User management
  └── Role management

MAINTAINER (level 2)
  ├── All USER permissions
  └── Delete operations

USER (level 1)
  ├── Read operations
  ├── Create operations (except user/role management)
  └── Basic functionality
```

### Database Schema
The RBAC system uses the following database tables:

**roles table:**
- `id` (UUID) - Primary key
- `name` (String) - Role name (USER, MAINTAINER, ADMIN)
- `created_at`, `updated_at` - Timestamps

**users table:**
- `id` (UUID) - Primary key, matches JWT subject
- `role_id` (UUID) - Foreign key to roles table
- `created_at`, `updated_at` - Timestamps

## Setup and Configuration

### 1. Database Migration
Run the database migration to create default roles:

```bash
alembic upgrade head
```

This will create the three default roles (USER, MAINTAINER, ADMIN) in the roles table.

### 2. Creating Users
Use the management script to create users with roles:

```bash
# Create an admin user
python scripts/manage_roles.py create-user --role ADMIN --id "admin-user-id"

# Create a maintainer user
python scripts/manage_roles.py create-user --role MAINTAINER --id "maintainer-user-id"

# Create a regular user
python scripts/manage_roles.py create-user --role USER --id "regular-user-id"
```

### 3. Generating Test Tokens
Generate JWT tokens for testing different roles:

```bash
# Generate token for admin user
python scripts/generate_test_token.py "admin-user-id"

# Generate token for maintainer user
python scripts/generate_test_token.py "maintainer-user-id"

# Generate token for regular user
python scripts/generate_test_token.py "regular-user-id"
```

## Testing RBAC

### Test Scenarios

1. **USER Role Test:**
   ```bash
   # This should work (read access)
   curl -H "Authorization: Bearer <user-token>" http://localhost:8000/datasets
   
   # This should fail (delete access)
   curl -X DELETE -H "Authorization: Bearer <user-token>" http://localhost:8000/datasets/some-id
   ```

2. **MAINTAINER Role Test:**
   ```bash
   # This should work (delete access)
   curl -X DELETE -H "Authorization: Bearer <maintainer-token>" http://localhost:8000/datasets/some-id
   
   # This should fail (user management)
   curl -X POST -H "Authorization: Bearer <maintainer-token>" http://localhost:8000/users
   ```

3. **ADMIN Role Test:**
   ```bash
   # This should work (user management)
   curl -X POST -H "Authorization: Bearer <admin-token>" \
        -H "Content-Type: application/json" \
        -d '{"id":"new-user","role_id":"role-id"}' \
        http://localhost:8000/users
   ```

## Management Scripts

### List Users and Roles
```bash
# List all users
python scripts/manage_roles.py list users

# List all roles
python scripts/manage_roles.py list roles
```

### Update User Roles
```bash
# Promote a user to MAINTAINER
python scripts/manage_roles.py update-role user-id MAINTAINER

# Promote a user to ADMIN
python scripts/manage_roles.py update-role user-id ADMIN
```

## Error Handling

The RBAC system returns appropriate HTTP status codes:

- **401 Unauthorized**: Invalid or missing authentication token
- **403 Forbidden**: Valid token but insufficient role permissions
- **404 Not Found**: Resource not found (after authorization check)

Error messages include information about required role levels:
```json
{
  "detail": "Insufficient privileges. Required role: MAINTAINER or higher"
}
```

## Security Considerations

1. **Token Expiration**: JWT tokens have configurable expiration times
2. **Role Validation**: Roles are validated on every request by looking up current user role in database
3. **Hierarchical Permissions**: Higher roles automatically inherit lower role permissions
4. **Database Integrity**: Foreign key constraints ensure referential integrity between users and roles
5. **Admin Protection**: System prevents deletion of roles that are still assigned to users

## Future Enhancements

Potential future improvements to the RBAC system:

1. **Resource-Level Permissions**: More granular permissions per resource type
2. **Tenant-Specific Roles**: Different role definitions per tenant
3. **Permission Caching**: Cache role lookups to improve performance
4. **Audit Logging**: Log all role-based access decisions
5. **Dynamic Roles**: Support for custom role creation with specific permission sets
