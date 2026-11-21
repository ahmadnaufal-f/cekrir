# Roles, permissions, and locations

The `roles` and `permissions` tables use UUID primary keys and unique readable codes. `role_permissions` associates their IDs with a composite primary key, so the same permission cannot be assigned to a role twice. Each user references a role by UUID. JWTs and API responses continue to use the readable role code. The migration preserves existing users, roles, and assignments.

For each authenticated request, middleware loads the current permissions from PostgreSQL. An access token's role claim is informational; changing a role's permissions or a user's role takes effect on the next request. Each protected HTTP route declares its required permission in its decorator:

```python
from fastapi import Depends
from cekrir.middleware import RequirePermission

@router.post("/example", dependencies=[Depends(RequirePermission("shipments:create"))])
def create_example():
    ...
```

Use an existing permission code from the `permissions` table. A protected `/api/v1/` route without a `RequirePermission` dependency is denied by default; explicitly public authentication routes are exempt. Camera ingestion routes use `RequirePermission("detections:create", allow_ingest_key=True)`, which preserves their configured ingestion-key authentication. Without an ingestion key configured, they require a bearer token with that permission. A live notification WebSocket checks the permission when it connects and does not use the HTTP dependency.

Each `locations` row has exactly one `admin_user_id`. One admin user can own multiple locations. Composite foreign keys and a check constraint ensure the referenced user has the `admin` role. When creating a location through the ORM, set `admin` to the administrator's `User` object so the matching role UUID is populated. Transfer ownership or delete the location before changing the user's role; the API returns 409 if the role change violates that constraint. `location_members` associates users with locations; `camera_devices` assigns each camera ID to at most one location. An owning admin can list locations and add members or cameras through the location endpoints. Location membership is used to select email recipients; the existing in-app notification feed remains global.

Run `pnpm run db:deploy` to apply the migrations before starting the updated backend. See `apps/backend/migrations/versions/20261117_0004_roles_permissions_locations.py` for the seeded permission names.
