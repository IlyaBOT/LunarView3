# Datasheet sources and verification record

Checked 2026-10-06. Original manufacturer documents are used; obsolete National/Intel documents are retrieved through archive/distributor mirrors. Search snippets and programmer device lists are not programming-algorithm evidence.

| Part / source | Checks used in this design |
|---|---|
| [National NM27C512, TL/D/10834, February 1994](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/National%20Semiconductor/Memory%20Components/National%20NM27C512.pdf) | DIP28 every pin, family package comparison, read/program rails and Fast Algorithm; pages 2,3,5,6,7 |
| [ATmel/Microchip ATmega328P](https://ww1.microchip.com/downloads/aemDocuments/documents/MCU08/ProductDocuments/DataSheets/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf) | TQFP32 numbering, GPIO/SPI/UART, ADC6/7, clock/reset/watchdog |
| [WCH CH340, v3B](https://cdn.sparkfun.com/assets/5/0/a/8/5/CH340DS1.PDF) | CH340C internal clock, V3 decoupling, pin8 OUT#/optional DTR2, NC pin7, DTR# pin13, R232 pin15 |
| [Nexperia 74HC/HCT595](https://assets.nexperia.com/documents/data-sheet/74HC_HCT595.pdf) | SO16 pins and cascade/control roles |
| [TI SN74HCT245](https://www.ti.com/lit/ds/symlink/sn74hct245.pdf) | DW wide-SOIC20 pins, DIR/OE and TTL input thresholds |
| [Nexperia 74LVC1G08](https://assets.nexperia.com/documents/data-sheet/74LVC1G08.pdf) | 5 V operation, GV SOT753 pin order 1B/2A/3GND/4Y/5VCC; RESET gating |
| [Omron G5V-2](https://omronfs.omron.com/en_US/ecb/products/pdf/en-g5v_2.pdf) | Standard DC5 coil 100 mA, bottom-view contacts, mounting layout; use G5V-2, not the H1 coil by assumption |
| [Infineon IRF9540N](https://www.infineon.com/dgdl/irf9540npbf.pdf?fileId=5546d462533600a401535611c1d31dc8) | P-channel 100 V, TO220 G1/D2/S3, VGS limit; D5 clamp polarity |
| [TI LM317](https://www.ti.com/lit/ds/symlink/lm317.pdf) | TO220 ADJ1/OUT2/IN3, reference/current/load, output-to-input protection diode |
| [Nexperia BAT54S](https://assets.nexperia.com/documents/data-sheet/BAT54S.pdf) | SOT23 pin1 anode, pin2 cathode, pin3 series midpoint; external clamps |
| [Topdiode BAT54WS](https://www.topdiode.com/pdf/BAT54WS.pdf) | SOD323 K1/A2; RESET positive-edge clamp |
| [Diodes MMBT5401](https://www.diodes.com/datasheet/download/MMBT5401.pdf) and [MMBT5551](https://www.diodes.com/datasheet/download/MMBT5551.pdf) | SOT23 B1/E2/C3; 150 V PNP and 160 V NPN pulse-stage parts |
| [Nexperia MMBT3904](https://assets.nexperia.com/documents/data-sheet/MMBT3904.pdf) and [MMBT3906](https://assets.nexperia.com/documents/data-sheet/MMBT3906.pdf) | SOT23 B1/E2/C3; relay/PMOS gate drive and UART LED buffers |
| [Kingbright KAAF-5050RGBS-13, Ver.3B](https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KAAF-5050RGBS-13%28Ver.3B%29.pdf) | Square analog RGB 5x5mm; physical 1R/2G/3B cathodes, 4/5/6 anodes; page 7 recommended 2.2x1.1mm lands and spacing |
| [Kingbright WP154A4SEJ3VBDZGW/CA](https://www.kingbrightusa.com/images/catalog/SPEC/WP154A4SEJ3VBDZGW-CA.pdf) | Four-lead 5mm RGB common anode; physical 1R/2A/3B/4G; 1.27mm lead pitch and mechanical package dimensions |
| [Intel 2716](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/Intel%202716.pdf) | DIP24 pinout and READ table; VPP21 = +5 V, VCC24, CE18, OE20 |
| [Intel 2732](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/Intel%202732.pdf) | DIP24; A11 pin21, OE/VPP pin20 |
| [Intel 2764](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/Intel%202764.pdf) | DIP28; VPP1, NC26, PGM27 and read mode |
| [Intel 27128A](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/Intel%2027128A.pdf) | DIP28; A13 pin26, PGM27; exact A variant |
| [Intel 27256](https://deramp.com/downloads/mfe_archive/050-Component%20Specifications/Intel/Memory%20Components/Intel%2027256.pdf) | DIP28; VPP1, A14 pin27, read mode; scan has a malformed PDF page object, first-page pin drawing was rendered |
| [National NM27C010](https://datasheets.pl/elementy_czynne/IC/NM/NM27C010-2.pdf) | DIP32, A0-A16, VPP1/PGM31, pin30 XX, read VCC and VPP condition; pages 2/3 |
| [Fairchild NM27C020, July 1998](https://www.pselectronic.cz/pdf/1125/11250125.pdf) | DIP32, A17 pin30, read VCC and VPP condition; pages 2/4 |
| [National NM27C040](https://docs.rs-online.com/a680/0900766b80025540.pdf) | DIP32, A18 pin31, CE/PGM22, read VCC and VPP condition; pages 2/3 |

KR573RF5 update, 2026-10-07: a separate read-only hardware PCB is provided in `Adapter-KR573RF5`. Its 24-pin mapping, published TTL output limit and access time were checked against the [two-page supplier technical sheet](https://storage.ua.prom.st/1093634_kr573rf5.pdf), issued by Electronics and Communications (eandc.ru). This is not an authenticated factory passport. It agrees with the Intel 2716 read pin arrangement; the adapter ties VPP21 to +5 V and uses HCT245 for TTL-to-CMOS data levels. Details and engineering assumptions are in the adapter README. The original factory operating/programming document is still missing; firmware profile mappings and commands remain disabled. No approximately 25 V programming algorithm has been validated or implemented for RF5.

NM27C080: package roles are present in National's family comparison, but an exact device read/algorithm sheet was not obtained. A19 is pin1 and OE/VPP pin24 in that comparison; its commands remain disabled. This avoids converting a package comparison into an unsupported claim of complete device validation.

The KiCad library CH340C pin8 is marked NC in this installation; WCH describes its output/optional second DTR function. ProjectSymbols:CH340C_WCH corrects pin8's type/name while preserving the package numbers. Pin8 still has an explicit NC marker in this circuit. The RGB alternative mounting footprint is project-local; its logical pad numbers preserve 1R/2A/3G/4B while physical manufacturer numbers are documented in RGB_Mounting.md. All remaining footprints are installed KiCad footprints. KiCad 10 names the USB shell pin/pads SH; it is explicitly grounded.

The nominal data-bus and VPP-stage behavior described in README is engineering analysis of this circuit, not a manufacturer guarantee for the whole assembled programmer. No physical performance test is claimed.
