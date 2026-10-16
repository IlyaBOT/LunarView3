# Lite validation — 2026-10-06

| Check | Result |
|---|---|
| Installed KiCad CLI | 10.0.6 |
| ERC, all severities, no custom suppression | 0 errors / 0 warnings |
| Editable schematic | One A3 sheet, 39 components |
| Actual exported netlist audit | 504 checks passed |
| Footprints | All 39 assigned footprints exist; every symbol pin has a corresponding physical pad |
| PDF | One page exported and visually inspected |
| Saved PCB placement | 90×60 mm, rounded 2.5 mm corners, four 3.2 mm M3 mounting holes; 39 electrical + 4 mechanical footprints |
| PCB DRC with schematic parity | 0 violations / 0 parity issues; 134 unconnected items, no tracks |
| Reloaded PCB preservation audit | 182 checks passed against saved snapshots and expected placement |

The netlist audit checks all MCU/CH340C/EPROM pins, both address registers, the complete DIP-28 mapping, UART crossing, RESET/DTR/clamp orientation, ISP isolation, reset/control pull resistors, the common-anode RGB pin order, and both buffered serial LEDs. It also checks that only the five requested U-designated components are present, D0–D7 are direct MCU/EPROM connections, and there are no programming nets.

KiCad's standard default ignored checks remain unchanged; no project-specific severity suppression or ERC exclusion is used. In this direct USB-powered circuit the USB symbol itself supplies the power-output declarations, so additional PWR_FLAG symbols are unnecessary.

The RGB upgrade originally preserved all unrelated schematic and PCB objects. The subsequent Lite placement deliberately moved all 39 electrical footprints, preserving their identities, pad identities and net assignments. The PCB now has an outline and four mechanical mounting footprints; it has no tracks or copper zones. Its quartz value and RGB datasheet field match the saved schematic. No schematic objects were changed during placement. No hardware was assembled, flashed or read-tested. The Stage 2 firmware is not compatible with Lite. Source verification and the intended read operation are described in `../README.md`.

Evidence: `erc.json`, `netlist.xml`, `connectivity_audit.json`, `bom.json`, and `kicad_version.txt`. Reproduce with `../validate.ps1` from the Lite directory. The project and its local symbol/library tables are entirely contained in `Dumper-Lite/`; the optional regeneration/audit scripts are in the parent `tools/` directory.

The combined RGB footprint is local to this project. The earlier 78-check RGB audit in `../../validation/rgb_mount_audit.json` records the RGB upgrade before placement; its assertion that every unrelated footprint stayed in the same position is historical. Current placement evidence: `placement_audit.json`, `placement_verification.json`, `drc_placement.json`, `Placement_Top.png` and [PLACEMENT.md](PLACEMENT.md). Backups: `placement_backup/`. THT RGB lands were widened to 1.11 mm while retaining 0.9 mm drills; these four lands use a local 0.15 mm clearance. Mounting details: `../../docs/RGB_Mounting.md`.
