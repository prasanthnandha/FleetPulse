"""
FleetPulse — Synthetic Service Manual Generator
=================================================
Generates realistic service manual documents for each device model.
Each manual contains step-by-step repair procedures, safety warnings,
required tools, and difficulty ratings per component.

Output: data/synthetic/service_manuals/<device_model>.md

Usage:
    python -m src.rag.generate_service_manuals
"""

import json
import random
from pathlib import Path

from src.rag.generate_parts_catalog import DEVICE_MODELS

# ==============================================================================
# Repair Procedure Templates
# ==============================================================================

TOOLS_REQUIRED = {
    "battery": [
        "Pentalobe P2 screwdriver",
        "Suction cup",
        "Spudger",
        "Tweezers",
        "iOpener (heat pad)",
        "Battery adhesive strips",
    ],
    "display": [
        "Pentalobe P2 screwdriver",
        "Suction cup",
        "Spudger",
        "Heat gun",
        "Display adhesive",
        "Microfiber cloth",
    ],
    "logic_board": [
        "Phillips #000 screwdriver",
        "Tri-point Y000 screwdriver",
        "Spudger",
        "Tweezers",
        "Anti-static wrist strap",
        "Thermal paste",
    ],
    "charging_port": ["Pentalobe P2 screwdriver", "Spudger", "Tweezers", "Phillips #000 screwdriver"],
    "camera_module": ["Pentalobe P2 screwdriver", "Spudger", "Tweezers", "Phillips #000 screwdriver"],
    "speaker": ["Pentalobe P2 screwdriver", "Spudger", "Tweezers"],
    "antenna": ["Pentalobe P2 screwdriver", "Spudger", "Phillips #000 screwdriver", "SIM ejector tool"],
    "storage": ["Phillips #000 screwdriver", "Spudger", "Anti-static wrist strap", "Thermal pad"],
    "keyboard": ["Phillips #0 screwdriver", "Spudger", "Plastic pry tool", "Compressed air"],
    "trackpad": ["Phillips #0 screwdriver", "Spudger", "Plastic pry tool"],
}

SAFETY_WARNINGS = {
    "battery": [
        "⚠️ DANGER: Lithium-ion batteries can catch fire or explode if punctured, bent, or short-circuited.",
        "⚠️ Discharge battery below 25% before removal to reduce thermal runaway risk.",
        "⚠️ Do not use metal tools to pry the battery. Use only plastic spudgers.",
        "⚠️ If battery is swollen, do not attempt removal — contact hazmat disposal.",
        "⚠️ Work in a well-ventilated area. Have a fire-resistant container nearby.",
    ],
    "display": [
        "⚠️ OLED displays contain organic compounds — avoid prolonged skin contact with broken panels.",
        "⚠️ Wear safety glasses when handling cracked glass.",
        "⚠️ Disconnect the battery before handling display cables to avoid short circuits.",
    ],
    "logic_board": [
        "⚠️ Electrostatic discharge (ESD) can permanently damage logic board components.",
        "⚠️ Always wear an anti-static wrist strap grounded to the work surface.",
        "⚠️ Do not touch IC chips or solder joints directly with bare hands.",
    ],
}

DIFFICULTY_LEVELS = {
    "battery": ("Moderate", 3),
    "display": ("Difficult", 4),
    "logic_board": ("Expert", 5),
    "charging_port": ("Moderate", 3),
    "camera_module": ("Moderate", 3),
    "speaker": ("Easy", 2),
    "antenna": ("Moderate", 3),
    "storage": ("Moderate", 3),
    "keyboard": ("Moderate", 3),
    "trackpad": ("Easy", 2),
}

REPAIR_PROCEDURES = {
    "battery": [
        "Power off the device completely and wait 30 seconds.",
        "Remove the {connector_type} screws from the bottom edge of the device using the appropriate screwdriver.",
        "Apply heat to the back panel/bottom case for 2-3 minutes using an iOpener or heat gun (65°C max) to soften adhesive.",
        "Insert a suction cup near the bottom edge and gently pull to create a gap.",
        "Slide a plastic spudger along the edge to release adhesive clips. Do not insert deeper than 3mm.",
        "Carefully lift the back panel/bottom case and set aside.",
        "Locate the battery connector on the logic board. It is a press-fit connector near the {location}.",
        "Use a plastic spudger to gently disconnect the battery cable from the logic board.",
        "If the battery is adhered with pull tabs, slowly pull each tab at a 45° angle parallel to the battery surface.",
        "If pull tabs break, apply isopropyl alcohol (90%+) along the battery edges and wait 2 minutes for adhesive to dissolve.",
        "Carefully lift the battery out of the device. Do not bend or puncture.",
        "Clean the battery bay of any residual adhesive.",
        "Place new battery adhesive strips in the battery bay.",
        "Position the new battery ({part_number}) in the bay, pressing firmly to seat.",
        "Connect the battery cable to the logic board connector. Ensure it clicks into place.",
        "Replace the back panel/bottom case and secure with screws.",
        "Power on the device and verify battery is recognized. Run a calibration cycle (full charge → full discharge → full charge).",
    ],
    "display": [
        "Power off the device and remove the SIM tray.",
        "Remove the {connector_type} screws from the bottom edge.",
        "Apply heat around the edges of the display for 3-4 minutes (65°C max) to soften adhesive.",
        "Attach a suction cup to the lower portion of the display.",
        "While pulling the suction cup, insert an opening pick into the gap that forms.",
        "Slide the pick along all four edges to separate the display adhesive. Move slowly near cable locations.",
        "Carefully fold the display open like a book — do not fully detach yet.",
        "Disconnect the battery connector first using a plastic spudger.",
        "Remove the display cable bracket screws (usually 2-3 Phillips screws).",
        "Disconnect the display flex cables from the logic board.",
        "Remove the old display assembly.",
        "Transfer any components from old display to new (earpiece, sensors, shield plates).",
        "Connect the new display ({part_number}) flex cables to the logic board.",
        "Replace the display cable bracket and screws.",
        "Reconnect the battery.",
        "Test the display before sealing: check touch response, color accuracy, brightness, and 3D Touch/Haptic Touch if applicable.",
        "Apply new display adhesive strips around the frame.",
        "Carefully press the display into place, applying even pressure around all edges.",
        "Replace bottom screws.",
    ],
    "logic_board": [
        "⚠️ This is an expert-level repair. Data backup is mandatory before proceeding.",
        "Power off the device and disconnect from all power sources.",
        "Remove the back panel/bottom case following standard procedure.",
        "Disconnect the battery immediately.",
        "Photograph all cable connections and screw locations for reassembly reference.",
        "Disconnect all flex cables: display, battery, cameras, antennas, charging port, speakers.",
        "Remove all bracket screws and brackets covering flex cable connectors.",
        "Remove the SIM card tray and any RF shields.",
        "Remove the logic board mounting screws (note different screw lengths).",
        "Carefully lift the logic board from the {location} edge first.",
        "Transfer SIM card reader, any shields, and thermal paste from old board if applicable.",
        "Apply new thermal paste/thermal pad to the SoC area of the new logic board ({part_number}).",
        "Position the new logic board, aligning with mounting posts.",
        "Replace mounting screws in correct positions (refer to photos).",
        "Reconnect all flex cables in reverse order of removal.",
        "Replace all brackets and bracket screws.",
        "Reconnect the battery.",
        "Replace back panel/bottom case.",
        "Power on and verify all functions: display, touch, cameras, cellular, WiFi, Bluetooth, speakers, microphone.",
        "Re-pair the device with MDM if necessary. Device may require re-enrollment.",
    ],
    "charging_port": [
        "Power off the device.",
        "Remove the bottom case/back panel screws.",
        "Open the device following standard procedure.",
        "Disconnect the battery.",
        "Locate the charging port flex cable. It typically runs along the {location}.",
        "Remove the bracket screws covering the charging port connector.",
        "Disconnect the charging port flex cable from the logic board.",
        "Remove any additional screws securing the charging port assembly.",
        "Carefully peel the charging port flex cable from any adhesive.",
        "Remove the old charging port assembly.",
        "Position the new charging port ({part_number}) and secure with screws.",
        "Route and connect the flex cable to the logic board.",
        "Replace the bracket and screws.",
        "Reconnect the battery.",
        "Test charging with a known-good cable before sealing. Verify data transfer as well.",
        "Reassemble the device.",
    ],
}

# Simplified procedures for components not in REPAIR_PROCEDURES
DEFAULT_PROCEDURE = [
    "Power off the device completely.",
    "Remove the back panel/bottom case following standard procedure.",
    "Disconnect the battery.",
    "Locate the {component_type} assembly.",
    "Remove any screws or brackets securing the component.",
    "Disconnect the {component_type} flex cable from the logic board.",
    "Remove the old {component_type} assembly.",
    "Position the new {component_type} ({part_number}) and secure.",
    "Reconnect the flex cable to the logic board.",
    "Reconnect the battery.",
    "Test {component_type} functionality before reassembly.",
    "Reassemble the device.",
]


def generate_manual_for_device(device_model: str, device_info: dict, parts: list[dict]) -> str:
    """Generate a complete service manual Markdown document for a device."""
    random.seed(hash(device_model))

    connector_types = {
        "Apple": "Pentalobe",
        "Samsung": "Phillips #0",
        "Google": "Torx T3",
    }
    connector_type = connector_types.get(device_info["manufacturer"], "Phillips #0")

    locations = ["bottom-left corner", "center-right area", "top-right corner", "bottom edge"]

    lines = [
        f"# {device_model} — Service Manual",
        "",
        f"**Manufacturer:** {device_info['manufacturer']}",
        f"**Operating System:** {device_info['os']}",
        f"**Model Year:** {device_info['year']}",
        "",
        "---",
        "",
        "## General Safety Precautions",
        "",
        "1. Always power off the device and disconnect from power before servicing.",
        "2. Work on a clean, static-free surface with an anti-static mat.",
        "3. Wear an anti-static wrist strap grounded to the work surface.",
        "4. Keep screws organized by size and position — use a magnetic screw mat.",
        "5. Never force components. If resistance is met, check for hidden screws or adhesive.",
        "6. Document all cable positions with photos before disconnecting.",
        "",
        "---",
        "",
    ]

    for part in parts:
        component = part["component_type"]
        difficulty, difficulty_num = DIFFICULTY_LEVELS.get(component, ("Moderate", 3))
        location = random.choice(locations)

        lines.extend(
            [
                f"## {component.replace('_', ' ').title()} Replacement",
                "",
                f"**Part Number:** `{part['part_number']}`",
                f"**Supplier:** {part['supplier']}",
                f"**Cost:** ${part['cost_usd']:.2f}",
                f"**Estimated Repair Time:** {part['estimated_repair_time_hours']} hours",
                f"**Difficulty:** {difficulty} ({'★' * difficulty_num}{'☆' * (5 - difficulty_num)})",
                f"**Availability:** {part['availability']}",
                "",
            ]
        )

        # Safety warnings
        if component in SAFETY_WARNINGS:
            lines.append("### Safety Warnings")
            lines.append("")
            for warning in SAFETY_WARNINGS[component]:
                lines.append(f"- {warning}")
            lines.append("")

        # Required tools
        tools = TOOLS_REQUIRED.get(component, ["Spudger", "Phillips screwdriver", "Tweezers"])
        lines.append("### Required Tools")
        lines.append("")
        for tool in tools:
            lines.append(f"- {tool}")
        lines.append("")

        # Repair procedure
        procedure = REPAIR_PROCEDURES.get(component, DEFAULT_PROCEDURE)
        lines.append("### Repair Procedure")
        lines.append("")
        for i, step in enumerate(procedure, 1):
            formatted_step = step.format(
                part_number=part["part_number"],
                connector_type=connector_type,
                location=location,
                component_type=component.replace("_", " "),
            )
            lines.append(f"{i}. {formatted_step}")
        lines.append("")

        # Post-repair verification
        lines.extend(
            [
                "### Post-Repair Verification",
                "",
                f"- [ ] {component.replace('_', ' ').title()} is functioning correctly",
                "- [ ] All screws are replaced and tightened",
                "- [ ] No loose cables or connectors",
                "- [ ] Device powers on and completes boot",
                "- [ ] MDM compliance check passes",
                "- [ ] Battery calibration completed (if applicable)",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)


def main():
    """Generate service manuals for all devices."""
    # Load parts catalog
    catalog_path = Path("data/synthetic/parts_catalog.json")
    if not catalog_path.exists():
        print("Parts catalog not found — generating first...")
        from src.rag.generate_parts_catalog import generate_catalog

        catalog = generate_catalog()
        catalog_path.parent.mkdir(parents=True, exist_ok=True)
        with open(catalog_path, "w") as f:
            json.dump(catalog, f, indent=2)
    else:
        with open(catalog_path) as f:
            catalog = json.load(f)

    # Group parts by device
    parts_by_device = {}
    for part in catalog:
        dm = part["device_model"]
        parts_by_device.setdefault(dm, []).append(part)

    # Generate manuals
    output_dir = Path("data/synthetic/service_manuals")
    output_dir.mkdir(parents=True, exist_ok=True)

    for device_model, device_info in DEVICE_MODELS.items():
        parts = parts_by_device.get(device_model, [])
        if not parts:
            continue

        manual = generate_manual_for_device(device_model, device_info, parts)

        # Sanitize filename
        filename = device_model.replace(" ", "_").replace("/", "_").replace(".", "_") + ".md"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(manual)

    print(f"Generated {len(DEVICE_MODELS)} service manuals in {output_dir}")
    total_size = sum(f.stat().st_size for f in output_dir.glob("*.md"))
    print(f"Total corpus size: {total_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
