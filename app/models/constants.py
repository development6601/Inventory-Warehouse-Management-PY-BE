class RoleCode:
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class RoleName:
    ADMIN = "Admin"
    MANAGER = "Manager"
    STAFF = "Staff"


class UnitCode:
    """Fixed product units — source of truth in code (not a DB table)."""

    G = "G"
    KG = "KG"
    L = "L"
    UNIT = "UNIT"

    ALL: tuple[str, ...] = (G, KG, L, UNIT)

    NAMES: dict[str, str] = {
        G: "Gram",
        KG: "Kilogram",
        L: "Liter",
        UNIT: "Number",
    }

    LABELS: dict[str, str] = {
        G: "Gram (g)",
        KG: "Kilogram (kg)",
        L: "Liter (L)",
        UNIT: "Number (unit)",
    }

    ABBREVIATIONS: dict[str, str] = {
        G: "g",
        KG: "kg",
        L: "L",
        UNIT: "unit",
    }
