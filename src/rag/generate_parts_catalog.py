"""
FleetPulse — Synthetic Parts Catalog Generator
================================================
Generates a structured synthetic device parts catalog:
~50 device models × ~10 components each → part numbers, suppliers, repair times.

Output: data/synthetic/parts_catalog.json

Usage:
    python -m src.rag.generate_parts_catalog
"""

import hashlib
import json
import random
from pathlib import Path

# ==============================================================================
# Device & Component Definitions
# ==============================================================================

DEVICE_MODELS = {
    # Apple
    "iPhone 15 Pro": {"manufacturer": "Apple", "os": "iOS", "year": 2023},
    "iPhone 15": {"manufacturer": "Apple", "os": "iOS", "year": 2023},
    "iPhone 14 Pro": {"manufacturer": "Apple", "os": "iOS", "year": 2022},
    "iPhone 14": {"manufacturer": "Apple", "os": "iOS", "year": 2022},
    "iPhone 13": {"manufacturer": "Apple", "os": "iOS", "year": 2021},
    "iPhone SE 3": {"manufacturer": "Apple", "os": "iOS", "year": 2022},
    "iPad Pro 12.9 M2": {"manufacturer": "Apple", "os": "iPadOS", "year": 2022},
    "iPad Air M1": {"manufacturer": "Apple", "os": "iPadOS", "year": 2022},
    "MacBook Pro 14 M3": {"manufacturer": "Apple", "os": "macOS", "year": 2023},
    "MacBook Air M2": {"manufacturer": "Apple", "os": "macOS", "year": 2022},
    # Samsung
    "Galaxy S24 Ultra": {"manufacturer": "Samsung", "os": "Android", "year": 2024},
    "Galaxy S24": {"manufacturer": "Samsung", "os": "Android", "year": 2024},
    "Galaxy S23": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    "Galaxy A54": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    "Galaxy A34": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    "Galaxy Z Flip5": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    "Galaxy Z Fold5": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    "Galaxy Tab S9": {"manufacturer": "Samsung", "os": "Android", "year": 2023},
    # Google
    "Pixel 8 Pro": {"manufacturer": "Google", "os": "Android", "year": 2023},
    "Pixel 8": {"manufacturer": "Google", "os": "Android", "year": 2023},
    "Pixel 7a": {"manufacturer": "Google", "os": "Android", "year": 2023},
    "Pixel 7": {"manufacturer": "Google", "os": "Android", "year": 2022},
    "Pixel Fold": {"manufacturer": "Google", "os": "Android", "year": 2023},
    # Microsoft
    "Surface Pro 10": {"manufacturer": "Microsoft", "os": "Windows", "year": 2024},
    "Surface Pro 9": {"manufacturer": "Microsoft", "os": "Windows", "year": 2022},
    "Surface Laptop 5": {"manufacturer": "Microsoft", "os": "Windows", "year": 2022},
    "Surface Go 4": {"manufacturer": "Microsoft", "os": "Windows", "year": 2023},
    # Lenovo
    "ThinkPad X1 Carbon Gen 11": {"manufacturer": "Lenovo", "os": "Windows", "year": 2023},
    "ThinkPad T14s Gen 4": {"manufacturer": "Lenovo", "os": "Windows", "year": 2023},
    "ThinkPad X13 Gen 4": {"manufacturer": "Lenovo", "os": "Windows", "year": 2023},
    # Dell
    "Latitude 5540": {"manufacturer": "Dell", "os": "Windows", "year": 2023},
    "Latitude 7440": {"manufacturer": "Dell", "os": "Windows", "year": 2023},
    "XPS 13 Plus": {"manufacturer": "Dell", "os": "Windows", "year": 2023},
    # HP
    "EliteBook 840 G10": {"manufacturer": "HP", "os": "Windows", "year": 2023},
    "EliteBook 860 G10": {"manufacturer": "HP", "os": "Windows", "year": 2023},
    "ProBook 450 G10": {"manufacturer": "HP", "os": "Windows", "year": 2023},
    # OnePlus
    "OnePlus 12": {"manufacturer": "OnePlus", "os": "Android", "year": 2024},
    "OnePlus 11": {"manufacturer": "OnePlus", "os": "Android", "year": 2023},
    # Motorola
    "Moto G Power 2024": {"manufacturer": "Motorola", "os": "Android", "year": 2024},
    "Moto Edge 40 Pro": {"manufacturer": "Motorola", "os": "Android", "year": 2023},
    # Nokia
    "Nokia X30": {"manufacturer": "Nokia", "os": "Android", "year": 2022},
    # Xiaomi
    "Xiaomi 14": {"manufacturer": "Xiaomi", "os": "Android", "year": 2024},
    "Redmi Note 13 Pro": {"manufacturer": "Xiaomi", "os": "Android", "year": 2024},
    # Asus
    "ROG Phone 7": {"manufacturer": "Asus", "os": "Android", "year": 2023},
    # Sony
    "Xperia 1 V": {"manufacturer": "Sony", "os": "Android", "year": 2023},
    # Additional
    "Galaxy Book3 Pro": {"manufacturer": "Samsung", "os": "Windows", "year": 2023},
    "Chromebook Pixel": {"manufacturer": "Google", "os": "ChromeOS", "year": 2023},
    "IdeaPad Slim 5": {"manufacturer": "Lenovo", "os": "Windows", "year": 2023},
    "ZenBook 14": {"manufacturer": "Asus", "os": "Windows", "year": 2023},
    "Spectre x360 14": {"manufacturer": "HP", "os": "Windows", "year": 2023},
}

COMPONENT_TYPES = {
    "battery": {
        "description": "Rechargeable lithium-ion/polymer battery pack",
        "cost_range": (25, 120),
        "repair_time_range": (0.5, 2.0),
        "suppliers": ["LG Chem", "CATL", "Samsung SDI", "BYD", "Panasonic", "ATL"],
    },
    "display": {
        "description": "LCD/OLED display assembly with digitizer",
        "cost_range": (80, 450),
        "repair_time_range": (1.0, 3.0),
        "suppliers": ["Samsung Display", "LG Display", "BOE", "Sharp", "JDI", "AUO"],
    },
    "logic_board": {
        "description": "Main logic board / motherboard with SoC",
        "cost_range": (150, 600),
        "repair_time_range": (2.0, 4.0),
        "suppliers": ["Foxconn", "Pegatron", "Flex Ltd", "Jabil", "Celestica"],
    },
    "charging_port": {
        "description": "USB-C/Lightning charging port assembly",
        "cost_range": (10, 45),
        "repair_time_range": (0.5, 1.5),
        "suppliers": ["Foxconn", "JAE Electronics", "Molex", "TE Connectivity"],
    },
    "camera_module": {
        "description": "Rear/front camera module assembly",
        "cost_range": (30, 180),
        "repair_time_range": (1.0, 2.5),
        "suppliers": ["Sony Semiconductor", "Samsung Electro-Mechanics", "LG Innotek", "OmniVision"],
    },
    "speaker": {
        "description": "Speaker/earpiece assembly",
        "cost_range": (8, 35),
        "repair_time_range": (0.5, 1.5),
        "suppliers": ["AAC Technologies", "Goertek", "Knowles Corp"],
    },
    "antenna": {
        "description": "Cellular/WiFi/Bluetooth antenna module",
        "cost_range": (12, 50),
        "repair_time_range": (1.0, 2.0),
        "suppliers": ["Murata", "Qualcomm", "Skyworks", "Qorvo"],
    },
    "storage": {
        "description": "NAND flash storage module",
        "cost_range": (20, 200),
        "repair_time_range": (1.5, 3.0),
        "suppliers": ["Samsung", "SK Hynix", "Kioxia", "Micron", "Western Digital"],
    },
    "keyboard": {
        "description": "Keyboard assembly (laptops only)",
        "cost_range": (30, 120),
        "repair_time_range": (1.0, 2.5),
        "suppliers": ["Darfon", "Chicony", "Sunrex", "Primax"],
        "laptop_only": True,
    },
    "trackpad": {
        "description": "Trackpad/touchpad assembly (laptops only)",
        "cost_range": (20, 80),
        "repair_time_range": (0.5, 1.5),
        "suppliers": ["Synaptics", "Elan Microelectronics", "Alps Alpine"],
        "laptop_only": True,
    },
}


def _generate_part_number(device_model: str, component: str) -> str:
    """Generate a deterministic, realistic-looking part number."""
    seed = f"{device_model}_{component}"
    h = hashlib.md5(seed.encode()).hexdigest()

    # Format: MFR-COMP-HEXHEX (e.g., APL-BAT-A3F2C8)
    mfr_codes = {
        "Apple": "APL",
        "Samsung": "SAM",
        "Google": "GGL",
        "Microsoft": "MSF",
        "Lenovo": "LNV",
        "Dell": "DLL",
        "HP": "HPQ",
        "OnePlus": "OPL",
        "Motorola": "MOT",
        "Nokia": "NOK",
        "Xiaomi": "XMI",
        "Asus": "ASU",
        "Sony": "SNY",
    }
    comp_codes = {
        "battery": "BAT",
        "display": "DSP",
        "logic_board": "MLB",
        "charging_port": "CHG",
        "camera_module": "CAM",
        "speaker": "SPK",
        "antenna": "ANT",
        "storage": "STO",
        "keyboard": "KBD",
        "trackpad": "TPD",
    }

    manufacturer = DEVICE_MODELS[device_model]["manufacturer"]
    mfr = mfr_codes.get(manufacturer, "GEN")
    comp = comp_codes.get(component, "UNK")

    return f"{mfr}-{comp}-{h[:6].upper()}"


def generate_catalog() -> list[dict]:
    """Generate the complete parts catalog."""
    random.seed(42)
    catalog = []

    for device_model, device_info in DEVICE_MODELS.items():
        is_laptop = (
            device_info["os"] in ("Windows", "macOS", "ChromeOS")
            and "Book" in device_model
            or "Pad" not in device_model
            and "Surface" in device_model
            or "ThinkPad" in device_model
            or "Latitude" in device_model
            or "XPS" in device_model
            or "EliteBook" in device_model
            or "ProBook" in device_model
            or "IdeaPad" in device_model
            or "ZenBook" in device_model
            or "Spectre" in device_model
            or "MacBook" in device_model
        )

        for component, comp_info in COMPONENT_TYPES.items():
            # Skip laptop-only components for phones/tablets
            if comp_info.get("laptop_only") and not is_laptop:
                continue

            # Skip keyboard/trackpad for tablets too
            if component in ("keyboard", "trackpad") and (
                "iPad" in device_model or "Tab" in device_model or "Go" in device_model
            ):
                continue

            part_number = _generate_part_number(device_model, component)
            supplier = random.choice(comp_info["suppliers"])
            cost = round(random.uniform(*comp_info["cost_range"]), 2)
            repair_time = round(random.uniform(*comp_info["repair_time_range"]), 1)

            catalog.append(
                {
                    "device_model": device_model,
                    "manufacturer": device_info["manufacturer"],
                    "os": device_info["os"],
                    "year": device_info["year"],
                    "component_type": component,
                    "component_description": comp_info["description"],
                    "part_number": part_number,
                    "supplier": supplier,
                    "cost_usd": cost,
                    "estimated_repair_time_hours": repair_time,
                    "availability": random.choice(["in_stock", "in_stock", "in_stock", "backorder", "limited"]),
                    "warranty_months": random.choice([3, 6, 12]),
                }
            )

    return catalog


def main():
    """Generate and save the parts catalog."""
    output_dir = Path("data/synthetic")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "parts_catalog.json"

    catalog = generate_catalog()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(catalog)} parts across {len(DEVICE_MODELS)} device models")
    print(f"Saved to {output_path}")

    # Print summary
    by_component = {}
    for item in catalog:
        ct = item["component_type"]
        by_component[ct] = by_component.get(ct, 0) + 1

    print("\nParts by component type:")
    for comp, count in sorted(by_component.items()):
        print(f"  {comp}: {count}")

    return catalog


if __name__ == "__main__":
    main()
