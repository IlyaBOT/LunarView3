# Validation report — 2026-10-06

The editable Stage 2 project is `../NM27C512_Dumper.kicad_pro`, with a 12-sheet schematic and 143 components. The original 5 V read-only design is preserved in `../baseline_readonly/`, with 3 sheets and 32 components. Both saved PCBs contain the two RGB mounting alternatives. Lite subsequently received component placement, a 90×60 mm outline and four M3 mounting holes; Stage 2 still has no outline. Neither board has tracks.

## Completed checks

| Check | Result | Evidence |
|---|---|---|
| Installed KiCad CLI | 10.0.6 on Windows | `kicad_version.txt` |
| Stage 2 ERC | 0 errors, 0 warnings | `erc.json` |
| Read-only ERC | 0 errors, 0 warnings | `baseline_erc.json` |
| Exported netlist and footprint audit | 1652 checks passed | `connectivity_audit.json`, both netlist XML files |
| Footprints | All 143 Stage 2 and 32 baseline components have assigned existing footprints (project-local RGB, installed KiCad footprints for the rest); all symbol pins have matching pads | `BOM.csv`, `baseline_BOM.csv`, audit report |
| RGB physical mapping and preservation, before Lite placement | 78 checks passed at the RGB upgrade stage | `rgb_mount_audit.json` |
| Current Lite placement | 0 DRC violations / 0 schematic parity issues; 134 unconnected items | `../Dumper-Lite/validation/PLACEMENT.md` |
| Host protocol tests | 19 tests passed | `host_tests.txt` |
| Safe AVR firmware | Compiles with avr-gcc 7.3.0, `-Wall -Wextra -Werror`; 4224 bytes flash / 235 bytes static RAM | `firmware_build_safe.txt` |
| WRITE-enabled compile check | Compiles with the same strict flags; 5542 bytes flash / 319 bytes static RAM | `firmware_build_commissioned.txt` |
| PDF export and visual QA | All 12 Stage 2 pages and all 3 baseline pages inspected | `NM27C512_Dumper.pdf`, `NM27C512_ReadOnly.pdf` |

ERC has no project-specific severity suppression or exclusions. KiCad's default ignored checks are documented in README. The separate audit checks pin mapping and assigned footprint existence/pad coverage, including the USB shield, CH340C, relay, MOSFET, regulator, clamps, data buffer and ADC dividers. It does not simulate switching waveforms, parasitic paths or component faults.

## Hardware status and remaining bench work

This is a schematic/prototype basis. No board was assembled, no EPROM was read or programmed, no serial port was opened, and no MCU was flashed in this task. The safe firmware is the default. The commissioned HEX is a compilation artifact, built with nominal bandgap calibration, and is not approval to program an untested board.

Before enabling WRITE, follow `../docs/bringup.md`: verify supply stability, calibrate the 6.25 V rail and ADC reference, verify relay isolation and reset/ISP/DTR fault behavior, and measure the actual NM27C512 pin 22 waveform under load. The NM27C512 programming requirement of VPP rise time at most 50 ns and no overshoot to 14 V is not proven by ERC. Redesign the VPP pulse stage if the measured waveform fails; leave WRITE locked until the circuit passes.

The National NM27C512 programming algorithm is source-verified and implemented. Other programming profiles remain disabled. KR573RF5 and NM27C080 read profiles also remain disabled because the exact manufacturer pinout/operating datasheet was not confirmed; their pending status is explicit in `../docs/device_profiles.md`. The hardware exposes A0–A19 and external VPP up to 25 V, but that alone does not establish device compatibility.

## Reproduction

From the project directory, run `./tools/validate.ps1 -BuildCommissioned`. This reruns both ERC checks, exports both netlists/PDFs, audits connectivity and footprints, runs the host tests, and compiles both firmware variants. It does not flash hardware or access a serial port.

See `../README.md`, `../docs/sources.md`, `../docs/protocol.md`, and `../docs/bringup.md` for the BOM, exact pin maps, primary sources, serial protocol and commissioning procedure. `artifact_hashes.json` records SHA-256 hashes of the delivered editable schematics, profile manifest, software sources, HEX files and PDF exports.

The original RGB change was verified with Stage 2/Lite ERC, XML netlist exports, connectivity/footprint audits and PDF exports. Existing host tests and firmware compile evidence were retained; firmware was unchanged. The current saved Stage 2 omits the user-removed POWER LED D1 and R6. During the subsequent Lite placement, all electrical pad identities and net assignments were preserved. Stage 2 placement was preserved; its RGB D2 THT land width/local clearance and text sizes were corrected together with the corresponding Lite/library geometry. Current placement evidence and backups are in `../Dumper-Lite/validation/`. Physical route requirements and manufacturer pin mappings are in `../docs/RGB_Mounting.md`.
