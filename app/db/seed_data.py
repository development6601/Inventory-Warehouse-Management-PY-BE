"""RBAC catalog + Module 2 sample catalog used by the seed script.

ADMIN receives every permission listed here (and should receive
every new permission added in later modules).
"""

from app.models.constants import RoleCode, RoleName, UnitCode

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
        "name": "category.create",
        "module": "category",
        "action": "create",
        "description": "Create product category",
    },
    {
        "name": "category.list",
        "module": "category",
        "action": "list",
        "description": "List product categories",
    },
    {
        "name": "category.view",
        "module": "category",
        "action": "view",
        "description": "View product category details",
    },
    {
        "name": "category.update",
        "module": "category",
        "action": "update",
        "description": "Update product category",
    },
    {
        "name": "category.status",
        "module": "category",
        "action": "status",
        "description": "Activate or deactivate product category",
    },
    {
        "name": "product.create",
        "module": "product",
        "action": "create",
        "description": "Create product",
    },
    {
        "name": "product.list",
        "module": "product",
        "action": "list",
        "description": "List products",
    },
    {
        "name": "product.view",
        "module": "product",
        "action": "view",
        "description": "View product details",
    },
    {
        "name": "product.update",
        "module": "product",
        "action": "update",
        "description": "Update product and manage images",
    },
    {
        "name": "product.status",
        "module": "product",
        "action": "status",
        "description": "Activate or deactivate product",
    },
    {
        "name": "unit.list",
        "module": "unit",
        "action": "list",
        "description": "List fixed units of measure",
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
        "category.list",
        "category.view",
        "product.list",
        "product.view",
        "unit.list",
    ],
    RoleCode.STAFF: [
        "user.view",
        "warehouse.list",
        "warehouse.view",
        "category.list",
        "category.view",
        "product.list",
        "product.view",
        "unit.list",
    ],
}

# Sample catalog for DB verification / Swagger prep (idempotent by name/sku)
SAMPLE_CATEGORIES: list[dict[str, str]] = [
    {
        "name": "Grains",
        "description": "Rice, wheat, and other grain products",
    },
    {
        "name": "Oils",
        "description": "Cooking oils and liquid fats",
    },
    {
        "name": "Packaged Goods",
        "description": "Counted packaged items",
    },
]

# Placeholder image URLs (external only — not stored on our servers)
_SAMPLE_IMAGE = "https://placehold.co/600x400.png"

SAMPLE_PRODUCTS: list[dict] = [
    {
        "sku": "RICE-1KG",
        "name": "Basmati Rice 1kg",
        "description": "Sample grain product",
        "category_name": "Grains",
        "unit_code": UnitCode.KG,
        "minimum_stock_threshold": "10.000",
        "price": "120.00",
        "image_urls": [_SAMPLE_IMAGE],
    },
    {
        "sku": "OIL-1L",
        "name": "Sunflower Oil 1L",
        "description": "Sample liquid product",
        "category_name": "Oils",
        "unit_code": UnitCode.L,
        "minimum_stock_threshold": "5.000",
        "price": "180.00",
        "image_urls": [_SAMPLE_IMAGE, f"{_SAMPLE_IMAGE}?text=oil-2"],
    },
    {
        "sku": "SOAP-100",
        "name": "Hand Soap Bar",
        "description": "Sample counted product",
        "category_name": "Packaged Goods",
        "unit_code": UnitCode.UNIT,
        "minimum_stock_threshold": "20.000",
        "price": "35.00",
        "image_urls": [_SAMPLE_IMAGE],
    },
]
