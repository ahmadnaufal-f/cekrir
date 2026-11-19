# Roles, permissions, and locations

The `roles` and `permissions` tables use UUID primary keys and unique readable codes. `role_permissions` associates their IDs with a composite primary key, so the same permission cannot be assigned to a role twice. Each user references a role by UUID. JWTs and API responses continue to use the readable role code. The migration preserves existing users, roles, and assignments.

For each authenticated request, middleware loads the current permissions from PostgreSQL. An access token's role claim is informational; changing a role's permissions or a user's role takes effect on the next request. Unmapped routes are denied until assigned a permission in the middleware. Camera ingestion still accepts its configured ingestion key. A live notification connection checks the permission when it connects.

Each `locations` row has exactly one `admin_user_id`. One admin user can own multiple locations. Composite foreign keys and a check constraint ensure the referenced user has the `admin` role. When creating a location through the ORM, set `admin` to the administrator's `User` object so the matching role UUID is populated. Transfer ownership or delete the location before changing the user's role; the API returns 409 if the role change violates that constraint. Location members and their permissions are not yet modeled, and no location API is exposed yet.

Run `pnpm run db:deploy` to apply the migrations before starting the updated backend. See `apps/backend/migrations/versions/20261117_0004_roles_permissions_locations.py` for the seeded permission names.
