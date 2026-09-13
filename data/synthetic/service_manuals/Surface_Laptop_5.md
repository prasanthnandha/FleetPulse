# Surface Laptop 5 — Service Manual

**Manufacturer:** Microsoft
**Operating System:** Windows
**Model Year:** 2022

---

## General Safety Precautions

1. Always power off the device and disconnect from power before servicing.
2. Work on a clean, static-free surface with an anti-static mat.
3. Wear an anti-static wrist strap grounded to the work surface.
4. Keep screws organized by size and position — use a magnetic screw mat.
5. Never force components. If resistance is met, check for hidden screws or adhesive.
6. Document all cable positions with photos before disconnecting.

---

## Battery Replacement

**Part Number:** `MSF-BAT-333FA5`
**Supplier:** CATL
**Cost:** $119.94
**Estimated Repair Time:** 1.8 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Safety Warnings

- ⚠️ DANGER: Lithium-ion batteries can catch fire or explode if punctured, bent, or short-circuited.
- ⚠️ Discharge battery below 25% before removal to reduce thermal runaway risk.
- ⚠️ Do not use metal tools to pry the battery. Use only plastic spudgers.
- ⚠️ If battery is swollen, do not attempt removal — contact hazmat disposal.
- ⚠️ Work in a well-ventilated area. Have a fire-resistant container nearby.

### Required Tools

- Pentalobe P2 screwdriver
- Suction cup
- Spudger
- Tweezers
- iOpener (heat pad)
- Battery adhesive strips

### Repair Procedure

1. Power off the device completely and wait 30 seconds.
2. Remove the Phillips #0 screws from the bottom edge of the device using the appropriate screwdriver.
3. Apply heat to the back panel/bottom case for 2-3 minutes using an iOpener or heat gun (65°C max) to soften adhesive.
4. Insert a suction cup near the bottom edge and gently pull to create a gap.
5. Slide a plastic spudger along the edge to release adhesive clips. Do not insert deeper than 3mm.
6. Carefully lift the back panel/bottom case and set aside.
7. Locate the battery connector on the logic board. It is a press-fit connector near the top-right corner.
8. Use a plastic spudger to gently disconnect the battery cable from the logic board.
9. If the battery is adhered with pull tabs, slowly pull each tab at a 45° angle parallel to the battery surface.
10. If pull tabs break, apply isopropyl alcohol (90%+) along the battery edges and wait 2 minutes for adhesive to dissolve.
11. Carefully lift the battery out of the device. Do not bend or puncture.
12. Clean the battery bay of any residual adhesive.
13. Place new battery adhesive strips in the battery bay.
14. Position the new battery (MSF-BAT-333FA5) in the bay, pressing firmly to seat.
15. Connect the battery cable to the logic board connector. Ensure it clicks into place.
16. Replace the back panel/bottom case and secure with screws.
17. Power on the device and verify battery is recognized. Run a calibration cycle (full charge → full discharge → full charge).

### Post-Repair Verification

- [ ] Battery is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Display Replacement

**Part Number:** `MSF-DSP-1E7357`
**Supplier:** Sharp
**Cost:** $291.61
**Estimated Repair Time:** 2.1 hours
**Difficulty:** Difficult (★★★★☆)
**Availability:** in_stock

### Safety Warnings

- ⚠️ OLED displays contain organic compounds — avoid prolonged skin contact with broken panels.
- ⚠️ Wear safety glasses when handling cracked glass.
- ⚠️ Disconnect the battery before handling display cables to avoid short circuits.

### Required Tools

- Pentalobe P2 screwdriver
- Suction cup
- Spudger
- Heat gun
- Display adhesive
- Microfiber cloth

### Repair Procedure

1. Power off the device and remove the SIM tray.
2. Remove the Phillips #0 screws from the bottom edge.
3. Apply heat around the edges of the display for 3-4 minutes (65°C max) to soften adhesive.
4. Attach a suction cup to the lower portion of the display.
5. While pulling the suction cup, insert an opening pick into the gap that forms.
6. Slide the pick along all four edges to separate the display adhesive. Move slowly near cable locations.
7. Carefully fold the display open like a book — do not fully detach yet.
8. Disconnect the battery connector first using a plastic spudger.
9. Remove the display cable bracket screws (usually 2-3 Phillips screws).
10. Disconnect the display flex cables from the logic board.
11. Remove the old display assembly.
12. Transfer any components from old display to new (earpiece, sensors, shield plates).
13. Connect the new display (MSF-DSP-1E7357) flex cables to the logic board.
14. Replace the display cable bracket and screws.
15. Reconnect the battery.
16. Test the display before sealing: check touch response, color accuracy, brightness, and 3D Touch/Haptic Touch if applicable.
17. Apply new display adhesive strips around the frame.
18. Carefully press the display into place, applying even pressure around all edges.
19. Replace bottom screws.

### Post-Repair Verification

- [ ] Display is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Logic Board Replacement

**Part Number:** `MSF-MLB-DFE851`
**Supplier:** Jabil
**Cost:** $273.52
**Estimated Repair Time:** 3.1 hours
**Difficulty:** Expert (★★★★★)
**Availability:** in_stock

### Safety Warnings

- ⚠️ Electrostatic discharge (ESD) can permanently damage logic board components.
- ⚠️ Always wear an anti-static wrist strap grounded to the work surface.
- ⚠️ Do not touch IC chips or solder joints directly with bare hands.

### Required Tools

- Phillips #000 screwdriver
- Tri-point Y000 screwdriver
- Spudger
- Tweezers
- Anti-static wrist strap
- Thermal paste

### Repair Procedure

1. ⚠️ This is an expert-level repair. Data backup is mandatory before proceeding.
2. Power off the device and disconnect from all power sources.
3. Remove the back panel/bottom case following standard procedure.
4. Disconnect the battery immediately.
5. Photograph all cable connections and screw locations for reassembly reference.
6. Disconnect all flex cables: display, battery, cameras, antennas, charging port, speakers.
7. Remove all bracket screws and brackets covering flex cable connectors.
8. Remove the SIM card tray and any RF shields.
9. Remove the logic board mounting screws (note different screw lengths).
10. Carefully lift the logic board from the bottom-left corner edge first.
11. Transfer SIM card reader, any shields, and thermal paste from old board if applicable.
12. Apply new thermal paste/thermal pad to the SoC area of the new logic board (MSF-MLB-DFE851).
13. Position the new logic board, aligning with mounting posts.
14. Replace mounting screws in correct positions (refer to photos).
15. Reconnect all flex cables in reverse order of removal.
16. Replace all brackets and bracket screws.
17. Reconnect the battery.
18. Replace back panel/bottom case.
19. Power on and verify all functions: display, touch, cameras, cellular, WiFi, Bluetooth, speakers, microphone.
20. Re-pair the device with MDM if necessary. Device may require re-enrollment.

### Post-Repair Verification

- [ ] Logic Board is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Charging Port Replacement

**Part Number:** `MSF-CHG-420A8B`
**Supplier:** TE Connectivity
**Cost:** $39.15
**Estimated Repair Time:** 1.4 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Required Tools

- Pentalobe P2 screwdriver
- Spudger
- Tweezers
- Phillips #000 screwdriver

### Repair Procedure

1. Power off the device.
2. Remove the bottom case/back panel screws.
3. Open the device following standard procedure.
4. Disconnect the battery.
5. Locate the charging port flex cable. It typically runs along the top-right corner.
6. Remove the bracket screws covering the charging port connector.
7. Disconnect the charging port flex cable from the logic board.
8. Remove any additional screws securing the charging port assembly.
9. Carefully peel the charging port flex cable from any adhesive.
10. Remove the old charging port assembly.
11. Position the new charging port (MSF-CHG-420A8B) and secure with screws.
12. Route and connect the flex cable to the logic board.
13. Replace the bracket and screws.
14. Reconnect the battery.
15. Test charging with a known-good cable before sealing. Verify data transfer as well.
16. Reassemble the device.

### Post-Repair Verification

- [ ] Charging Port is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Camera Module Replacement

**Part Number:** `MSF-CAM-F30A2F`
**Supplier:** LG Innotek
**Cost:** $62.85
**Estimated Repair Time:** 1.3 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Required Tools

- Pentalobe P2 screwdriver
- Spudger
- Tweezers
- Phillips #000 screwdriver

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the camera module assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the camera module flex cable from the logic board.
7. Remove the old camera module assembly.
8. Position the new camera module (MSF-CAM-F30A2F) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test camera module functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Camera Module is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Speaker Replacement

**Part Number:** `MSF-SPK-6DAC58`
**Supplier:** Knowles Corp
**Cost:** $28.72
**Estimated Repair Time:** 1.2 hours
**Difficulty:** Easy (★★☆☆☆)
**Availability:** in_stock

### Required Tools

- Pentalobe P2 screwdriver
- Spudger
- Tweezers

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the speaker assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the speaker flex cable from the logic board.
7. Remove the old speaker assembly.
8. Position the new speaker (MSF-SPK-6DAC58) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test speaker functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Speaker is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Antenna Replacement

**Part Number:** `MSF-ANT-B28AF4`
**Supplier:** Murata
**Cost:** $46.33
**Estimated Repair Time:** 1.6 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Required Tools

- Pentalobe P2 screwdriver
- Spudger
- Phillips #000 screwdriver
- SIM ejector tool

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the antenna assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the antenna flex cable from the logic board.
7. Remove the old antenna assembly.
8. Position the new antenna (MSF-ANT-B28AF4) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test antenna functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Antenna is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Storage Replacement

**Part Number:** `MSF-STO-57613C`
**Supplier:** Samsung
**Cost:** $124.32
**Estimated Repair Time:** 2.6 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Required Tools

- Phillips #000 screwdriver
- Spudger
- Anti-static wrist strap
- Thermal pad

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the storage assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the storage flex cable from the logic board.
7. Remove the old storage assembly.
8. Position the new storage (MSF-STO-57613C) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test storage functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Storage is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Keyboard Replacement

**Part Number:** `MSF-KBD-66F3A5`
**Supplier:** Sunrex
**Cost:** $97.27
**Estimated Repair Time:** 1.3 hours
**Difficulty:** Moderate (★★★☆☆)
**Availability:** in_stock

### Required Tools

- Phillips #0 screwdriver
- Spudger
- Plastic pry tool
- Compressed air

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the keyboard assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the keyboard flex cable from the logic board.
7. Remove the old keyboard assembly.
8. Position the new keyboard (MSF-KBD-66F3A5) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test keyboard functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Keyboard is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---

## Trackpad Replacement

**Part Number:** `MSF-TPD-EDC7BF`
**Supplier:** Elan Microelectronics
**Cost:** $51.85
**Estimated Repair Time:** 1.4 hours
**Difficulty:** Easy (★★☆☆☆)
**Availability:** in_stock

### Required Tools

- Phillips #0 screwdriver
- Spudger
- Plastic pry tool

### Repair Procedure

1. Power off the device completely.
2. Remove the back panel/bottom case following standard procedure.
3. Disconnect the battery.
4. Locate the trackpad assembly.
5. Remove any screws or brackets securing the component.
6. Disconnect the trackpad flex cable from the logic board.
7. Remove the old trackpad assembly.
8. Position the new trackpad (MSF-TPD-EDC7BF) and secure.
9. Reconnect the flex cable to the logic board.
10. Reconnect the battery.
11. Test trackpad functionality before reassembly.
12. Reassemble the device.

### Post-Repair Verification

- [ ] Trackpad is functioning correctly
- [ ] All screws are replaced and tightened
- [ ] No loose cables or connectors
- [ ] Device powers on and completes boot
- [ ] MDM compliance check passes
- [ ] Battery calibration completed (if applicable)

---
