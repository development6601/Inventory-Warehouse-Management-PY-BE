"""Module 1 RBAC catalog used by the seed script.

ADMIN receives every permission listed here (and should receive
every new permission added in later modules).
"""

from app.models.constants import RoleCode, RoleName

ROLES: list[dict[str, str]] = [
    {
        "code": RoleCode.ADMIN,
        "name": RoleName.ADMIN,
        "description": "Full system access; created via createsuperuser only",
    },
    {
        "code": RoleCode.MANAGER,
        "name": RoleName.MANAGER,
        "description": "Warehouse manager; assigned to one warehouse",
    },
    {
        "code": RoleCode.STAFF,
        "name": RoleName.STAFF,
        "description": "Warehouse staff; assigned to one warehouse",
    },
]

PERMISSIONS: list[dict[str, str]] = [
    {
        "name": "user.create",
        "module": "user",
        "action": "create",
        "description": "Create Manager or Staff users",
    },
    {
        "name": "user.list",
        "module": "user",
        "action": "list",
        "description": "List users",
    },
    {
        "name": "user.view",
        "module": "user",
        "action": "view",
        "description": "View user details",
    },
    {
        "name": "user.update",
        "module": "user",
        "action": "update",
        "description": "Update user fields (admin)",
    },
    {
        "name": "user.activate",
        "module": "user",
        "action": "activate",
        "description": "Activate or deactivate users",
    },
    {
        "name": "user.assign_warehouse",
        "module": "user",
        "action": "assign_warehouse",
        "description": "Assign user to warehouse as Staff or Manager",
    },
    {
        "name": "user.reset_password",
        "module": "user",
        "action": "reset_password",
        "description": "Admin force-reset password",
    },
    {
        "name": "warehouse.create",
        "module": "warehouse",
        "action": "create",
        "description": "Create warehouse",
    },
    {
        "name": "warehouse.list",
        "module": "warehouse",
        "action": "list",
        "description": "List warehouses",
    },
    {
        "name": "warehouse.view",
        "module": "warehouse",
        "action": "view",
        "description": "View warehouse details including managers",
    },
    {
        "name": "warehouse.update",
        "module": "warehouse",
        "action": "update",
        "description": "Update warehouse name or location",
    },
    {
        "name": "warehouse.status",
        "module": "warehouse",
        "action": "status",
        "description": "Activate or deactivate warehouse",
    },
    {
        "name": "warehouse.list_users",
        "module": "warehouse",
        "action": "list_users",
        "description": "List users assigned to a warehouse",
    },
    {
        "name": "audit.view",
        "module": "audit",
        "action": "view",
        "description": "View audit logs",
    },
]

# Role code -> permission names
ROLE_PERMISSION_MAP: dict[str, list[str]] = {
    RoleCode.ADMIN: [p["name"] for p in PERMISSIONS],
    RoleCode.MANAGER: [
        "user.view",
        "user.assign_warehouse",
        "warehouse.list",
        "warehouse.view",
        "warehouse.list_users",
    ],
    RoleCode.STAFF: [
        "user.view",
        "warehouse.list",
        "warehouse.view",
    ],
}
