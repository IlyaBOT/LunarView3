# Per-component BOM

## Stage 2

| Ref | Value | Footprint | Sheet |
| --- | --- | --- | --- |
| J1 | USB Micro-B | Connector_USB:USB_Micro-B_Molex-105017-0001 | controller.kicad_sch |
| F1 | 500mA hold | Fuse:Fuse_1812_4532Metric | controller.kicad_sch |
| C1 | 10uF / 10V | Capacitor_SMD:C_0805_2012Metric | controller.kicad_sch |
| U5 | CH340C | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | controller.kicad_sch |
| C2 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C3 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| R4 | 1k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| R5 | 1k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| U1 | ATmega328P-AU | Package_QFP:TQFP-32_7x7mm_P0.8mm | controller.kicad_sch |
| Y1 | 16MHz, CL ~18pF | Crystal:Crystal_HC49-4H_Vertical | controller.kicad_sch |
| C11 | 22pF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C12 | 22pF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| R1 | 10k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| SW1 | RESET | Button_Switch_THT:SW_PUSH_6mm | controller.kicad_sch |
| C13 | 100nF auto-reset | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| D9 | BAT54WS RESET clamp | Diode_SMD:D_SOD-323 | controller.kicad_sch |
| C4 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C5 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C6 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C10 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| J2 | AVR ISP | Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical | controller.kicad_sch |
| J3 | UART (MCU RX/TX) | Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical | controller.kicad_sch |
| U2 | 74HC595D | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | address_target.kicad_sch |
| C7 | 100nF | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| U3 | 74HC595D | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | address_target.kicad_sch |
| C8 | 100nF | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| U4 | 74HC595D | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | address_target.kicad_sch |
| C14 | 100nF | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| R7 | 10k LATCH pull-down | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| U6 | NM27C512Q SOCKET | Package_DIP:DIP-28_W15.24mm_Socket_LongPads | address_target.kicad_sch |
| C9 | 100nF / 16V | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| R2 | 10k CE pull-up | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| R3 | 10k OE pull-up | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| R8 | 10k PGM pull-up | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| C15 | 10uF / 16V | Capacitor_SMD:C_0805_2012Metric | address_target.kicad_sch |
| R10 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D10 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R11 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D11 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R12 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D12 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R13 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D13 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R14 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D14 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R15 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D15 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R16 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D16 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R17 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D17 | BAT54S | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| D2 | RGB CA / 5050 OR THT5 | ProjectFootprints:RGB_CA_5050_or_THT5 | data_status.kicad_sch |
| R20 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| R21 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| R22 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| Q1 | MMBT3906 | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R23 | 10k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| R25 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D3 | RX BLUE | LED_SMD:LED_0603_1608Metric | data_status.kicad_sch |
| Q2 | MMBT3906 | Package_TO_SOT_SMD:SOT-23 | data_status.kicad_sch |
| R24 | 10k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| R26 | 1k | Resistor_SMD:R_0603_1608Metric | data_status.kicad_sch |
| D4 | TX ORANGE | LED_SMD:LED_0603_1608Metric | data_status.kicad_sch |
| U9 | SN74HCT245DW | Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm | ttl_bus.kicad_sch |
| C26 | 100nF | Capacitor_SMD:C_0603_1608Metric | ttl_bus.kicad_sch |
| R50 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D20 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R51 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D21 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R52 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D22 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R53 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D23 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R54 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D24 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R55 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D25 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R56 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D26 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| R57 | 1k | Resistor_SMD:R_0603_1608Metric | ttl_bus.kicad_sch |
| D27 | BAT54S | Package_TO_SOT_SMD:SOT-23 | ttl_bus.kicad_sch |
| J4 | J_VPP_IN | TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal | programming_power.kicad_sch |
| C20 | 100nF / 50V | Capacitor_SMD:C_0603_1608Metric | programming_power.kicad_sch |
| Q3 | IRF9540N / 100V PMOS | Package_TO_SOT_THT:TO-220-3_Vertical | programming_power.kicad_sch |
| R30 | 47k gate-source | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| D5 | BZT52C10 / 10V | Diode_SMD:D_SOD-123 | programming_power.kicad_sch |
| R31 | 2.2k / 0.25W | Resistor_SMD:R_1206_3216Metric | programming_power.kicad_sch |
| Q4 | MMBT3904 | Package_TO_SOT_SMD:SOT-23 | programming_power.kicad_sch |
| R32 | 1k | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| R33 | 10k base pull-down | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| U10 | 74LVC1G08 / arm interlock | Package_TO_SOT_SMD:SOT-23-5 | programming_power.kicad_sch |
| C27 | 100nF | Capacitor_SMD:C_0603_1608Metric | programming_power.kicad_sch |
| R60 | 10k arm pull-down | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| C28 | 100nF / 50V | Capacitor_SMD:C_0603_1608Metric | programming_power.kicad_sch |
| R61 | 100k bleed | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| U7 | LM317T: calibrate 6.250 V | Package_TO_SOT_THT:TO-220-3_Vertical | programming_power.kicad_sch |
| C23 | 100nF / 50V | Capacitor_SMD:C_0603_1608Metric | programming_power.kicad_sch |
| C24 | 10uF / 16V | Capacitor_SMD:C_1206_3216Metric | programming_power.kicad_sch |
| R40 | 120R / 1% | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| R41 | 430R / 1% | Resistor_SMD:R_0603_1608Metric | programming_power.kicad_sch |
| RV1 | 100R multi-turn | Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical | programming_power.kicad_sch |
| D7 | 1N4007 output protection | Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal | programming_power.kicad_sch |
| Q7 | MMBT5401 / 150V PNP | Package_TO_SOT_SMD:SOT-23 | programming_pulse.kicad_sch |
| R62 | 10k base-emitter | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R63 | 2.2k / 0.25W | Resistor_SMD:R_1206_3216Metric | programming_pulse.kicad_sch |
| Q6 | MMBT5551 / 160V NPN | Package_TO_SOT_SMD:SOT-23 | programming_pulse.kicad_sch |
| R64 | 1k | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R65 | 10k | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| U8 | 74LVC1G08 / pulse interlock | Package_TO_SOT_SMD:SOT-23-5 | programming_pulse.kicad_sch |
| C21 | 100nF | Capacitor_SMD:C_0603_1608Metric | programming_pulse.kicad_sch |
| R34 | 10k VPP_EN pull-down | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R35 | 120k / 1% | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R36 | 22k / 1% | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| C22 | 10nF | Capacitor_SMD:C_0603_1608Metric | programming_pulse.kicad_sch |
| D30 | ADC6 BAT54S clamp | Package_TO_SOT_SMD:SOT-23 | programming_pulse.kicad_sch |
| R37 | 10k bleed | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R38 | 5.1k | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| R39 | 5.1k | Resistor_SMD:R_0603_1608Metric | programming_pulse.kicad_sch |
| D6 | VPP ACTIVE RED | LED_SMD:LED_0603_1608Metric | programming_pulse.kicad_sch |
| K1 | G5V-2-DC5 (100mA coil) | Relay_THT:Relay_DPDT_Omron_G5V-2 | target_interface.kicad_sch |
| Q5 | MMBT3904 | Package_TO_SOT_SMD:SOT-23 | target_interface.kicad_sch |
| R42 | 470R relay drive | Resistor_SMD:R_0603_1608Metric | target_interface.kicad_sch |
| R43 | 10k | Resistor_SMD:R_0603_1608Metric | target_interface.kicad_sch |
| R44 | 10k | Resistor_SMD:R_0603_1608Metric | target_interface.kicad_sch |
| D8 | 1N4148WS flyback | Diode_SMD:D_SOD-323 | target_interface.kicad_sch |
| R45 | 10k / 1% | Resistor_SMD:R_0603_1608Metric | target_interface.kicad_sch |
| R46 | 10k / 1% | Resistor_SMD:R_0603_1608Metric | target_interface.kicad_sch |
| C25 | 10nF | Capacitor_SMD:C_0603_1608Metric | target_interface.kicad_sch |
| D31 | ADC7 BAT54S clamp | Package_TO_SOT_SMD:SOT-23 | target_interface.kicad_sch |
| J5 | J_TARGET / 40-pin | Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical | target_interface.kicad_sch |
| TP1 | TP_5V | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP2 | TP_GND | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP3 | TP_6V25 | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP4 | TP_VPP_IN | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP5 | TP_VPP_SW | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP6 | TP_RESET | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP7 | TP_ADDR_SCK | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP8 | TP_ADDR_LATCH | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP9 | TP_CE | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP10 | TP_OE | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP11 | TP_PGM | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP12 | TP_RX | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |
| TP13 | TP_TX | TestPoint:TestPoint_Pad_D1.5mm | testpoints_safety.kicad_sch |

## Original 5 V read-only baseline

| Ref | Value | Footprint | Sheet |
| --- | --- | --- | --- |
| J1 | USB Micro-B | Connector_USB:USB_Micro-B_Molex-105017-0001 | controller.kicad_sch |
| F1 | 500mA hold | Fuse:Fuse_1812_4532Metric | controller.kicad_sch |
| C1 | 10uF / 10V | Capacitor_SMD:C_0805_2012Metric | controller.kicad_sch |
| U4 | CH340C | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | controller.kicad_sch |
| C2 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C3 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| R4 | 1k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| R5 | 1k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| U1 | ATmega328P-AU | Package_QFP:TQFP-32_7x7mm_P0.8mm | controller.kicad_sch |
| Y1 | 16MHz, CL ~18pF | Crystal:Crystal_HC49-4H_Vertical | controller.kicad_sch |
| C11 | 22pF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C12 | 22pF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| R1 | 10k | Resistor_SMD:R_0603_1608Metric | controller.kicad_sch |
| SW1 | RESET | Button_Switch_THT:SW_PUSH_6mm | controller.kicad_sch |
| C13 | 100nF auto-reset | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C4 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C5 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C6 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| C10 | 100nF | Capacitor_SMD:C_0603_1608Metric | controller.kicad_sch |
| J2 | AVR ISP | Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical | controller.kicad_sch |
| J3 | UART (MCU RX/TX) | Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical | controller.kicad_sch |
| U2 | 74HC595D | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | address_target.kicad_sch |
| C7 | 100nF | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| U3 | 74HC595D | Package_SO:SOIC-16_3.9x9.9mm_P1.27mm | address_target.kicad_sch |
| C8 | 100nF | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| R7 | 10k LATCH pull-down | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| U5 | NM27C512Q SOCKET | Package_DIP:DIP-28_W15.24mm_Socket_LongPads | address_target.kicad_sch |
| C9 | 100nF / 16V | Capacitor_SMD:C_0603_1608Metric | address_target.kicad_sch |
| R2 | 10k CE pull-up | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| R3 | 10k OE pull-up | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| R6 | 1k | Resistor_SMD:R_0603_1608Metric | address_target.kicad_sch |
| D1 | POWER GREEN | LED_SMD:LED_0603_1608Metric | address_target.kicad_sch |
