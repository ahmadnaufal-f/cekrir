# Roles, permissions, and locations

The `roles` and `permissions` tables use their unique names as primary keys. `role_permissions` associates the two with a composite primary key, so the same permission cannot be assigned to a role twice. Each user's existing `role` field references a role name. The migration seeds `admin` and `member` roles and grants the permissions needed for the existing endpoints.

For each authenticated request, middleware loads the current permissions from PostgreSQL. An access token's role claim is informational; changing a role's permissions or a user's role takes effect on the next request. Unmapped routes are denied until assigned a permission in the middleware. Camera ingestion still accepts its configured ingestion key. A live notification connection checks the permission when it connects.

Each `locations` row has exactly one `admin_user_id`. One admin user can own multiple locations. A composite foreign key and a check constraint ensure the referenced user has the `admin` role. Transfer ownership or delete the location before changing the user's role; the API returns 409 if the role change violates that constraint. Location members and their permissions are not yet modeled, and no location API is exposed yet.

Run `pnpm run db:deploy` to apply the migrations before starting the updated backend. See `apps/backend/migrations/versions/20261117_0004_roles_permissions_locations.py` for the seeded permission names.
