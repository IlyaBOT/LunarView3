> Историческое руководство Stage 2. Для новой платы **Lunar Writer** вход J4 принимает **12–24 В**, затем напряжение регулируется на плате: подключение и первичная калибровка описаны в [Lunar-Writer/README.md](../Lunar-Writer/README.md). Пункты ниже о внешнем готовом VPP и отсутствии входной защиты относятся к старой схеме. Текущая безопасная прошивка называется `writer_safe.hex`. GPIO, fuse-настройки, проверки импульсов и алгоритма остаются применимыми.

# Rev A bring-up and WRITE commissioning

The delivered circuit has been checked as a schematic. No assembled board, EPROM, oscilloscope or serial port was exercised. The safe firmware deliberately returns `HARDWARE_NOT_COMMISSIONED` for every WRITE. Compiling the commissioned variant verifies code compilation only; it does not commission hardware.

## Assembly and initial power

1. Leave U6 and J_TARGET empty. Check diode polarity, Q3 G/D/S = 1/2/3, Q6/Q7 B/E/C = 1/2/3, LM317 ADJ/OUT/IN = 1/2/3 and its live output tab. Check K1 against the Omron **bottom-view** terminal drawing. Fit the exact connector, regulator, MOSFET and relay packages from the BOM.
2. Initially connect only a current-limited 5 V USB supply. Check +5V and all logic supplies, CH340 V3 decoupling, RESET HIGH, CE/OE/PGM HIGH, PD2/PD3/PB1 LOW and K1 in READ. TARGET_VCC must equal +5V. Do not connect a competing ISP power source.
3. Program `writer_safe.hex` by ISP (current build name; the obsolete dumper_safe.hex is no longer shipped). There is no bootloader dependency. The firmware expects a real 16 MHz crystal and CKDIV8 disabled. Suggested ATmega328P settings, to verify against the actual part before writing: low `0xFF` (external crystal), high `0xD9` (SPI and RESET retained, watchdog controlled by software, no boot reset), extended `0xFC` (4.3 V brownout), lock `0xFF`. Fuse programming was not performed in this task.
4. Open the CH340 serial port at 57600 baud / 8N1. INFO must report protocol 1, matching profile hash and commissioned=0. The UBRR setting rounds to the nearest divisor: 57142.9 baud, -0.79% nominal error at 16 MHz.
5. Check SPI clocks, all A0-A19 outputs and RGB bits with a logic analyzer. Read and verify a known NM27C512 twice and compare the dumps with a trusted programmer before testing high voltage.

## External supply and 6.25 V calibration

The programming supply is external, regulated and shares GND. USB powers the entire logic/relay circuit. Never apply external VPP with USB absent. J4 pin1 is VPP_IN; pin2 is GND. Reverse-polarity, wrong-connector and arbitrary overvoltage protection are not implemented. Do not feed J_TARGET power rails from another supply.

For NM27C512, the required **measured switched output** is 12.50-13.00 V, nominal 12.75 V. Q7 has a load-dependent voltage drop, so its input cannot simply be assumed to equal VPP_SW. Use a current limit sized for the EPROM VPP current plus the LM317 load: about 150 mA is a practical starting point for this prototype; verify actual consumption. Other profiles never automatically reuse this voltage.

With the socket empty and K1 in READ, feed the regulator and adjust RV1 until TP_6V25 is 6.250 V. R40=120 ohm provides approximately 10.4 mA minimum load. R41=430 ohm plus the 0-100 ohm trimmer spans roughly 5.73-6.80 V; about 48 ohm of trim gives the nominal setting, subject to LM317 reference and Iadj. The wiper and one end are both grounded. Verify the rail again with a 100 ohm / at least 1 W temporary load (62.5 mA); remove the load afterward.

LM317 dissipation is `(VPP_IN-6.25)*I_OUT`. At 25 V and a 50 mA target plus 10.4 mA feedback, it is approximately 1.13 W. Provide a heatsink and verify temperature at the intended maximum input. The TO-220 tab is connected to OUT, not GND. Use 50 V input/arming capacitors and account for MLCC voltage derating; output/target capacitors are at least 16 V. There is no bulk capacitor on VPP_SW.

## ADC calibration

AVCC is the ADC reference. The internal nominal 1.1 V bandgap has substantial part-to-part tolerance; do not commission programming using the uncalibrated default. Measure AVCC with a calibrated meter, obtain the raw bandgap ADC reading in a temporary calibration firmware or debugger, and set `BandgapMillivolts = measured_AVCC_mV * raw / 1023`. Rebuild the safe variant with this value, then compare VOLTAGES against a meter at 5.00 V target and several VPP_SW values with the socket isolated. Verify the actual divider ratios as well as the bandgap.

R35/R36 are 120k/22k, 1%; R45/R46 are 10k/10k, 1%. Calibrate or select them if the accumulated error is significant relative to the 0.25 V VPP tolerance. ADC filtering, averaged conversions and voltage checks cannot stop a nanosecond overvoltage spike; correct switching waveforms must be established electrically.

## Pulse-stage acceptance checks

Keep a dummy load in place of the EPROM until these checks pass. This revision uses a slow PMOS arming stage followed by a discrete PNP pulse switch. Its required waveform performance has **not** been established by ERC or by compilation.

1. Test PB1 arming while the relay remains READ. Measure HV_ARM and VPP_SW. Test VPP_SW under the datasheet's programming load, up to 30 mA for NM27C512; a roughly 430 ohm / 1 W dummy load is useful at 12.75 V. Calibrate the supply for the measured output, including Q7 drop. Check the input maximum for the profile and do not adjust it while programming.
2. Scope actual socket pin22 during enabled pulses. The NM27C512 timing table specifies OE/VPP rise time no greater than 50 ns. Verify this at the loaded socket, with realistic PCB/adapter capacitance and proper short-ground probing. Overshoot must remain below the 14 V absolute maximum, with margin. If the discrete stage cannot meet the timing, redesign the pulse driver and revalidate; do not merely remove the WRITE lock.
3. Confirm a CE/PGM LOW pulse of approximately 100 us, address/data setup and hold, inactive OE logic isolation, data direction switching and valid programming VCC. Byte verify is done at 6.25 V with socket OE/VPP returned to LOW. Final comparison is at the normal 5 V rail.
4. Confirm VPP_SW drops below 0.40 V before byte verify; the firmware waits 3 ms for the ADC filter, then allows a bounded discharge wait. Inspect actual discharge at pin22 and relay transition behavior. A wiring fault or stuck transistor is outside the software safety guarantee.
5. Assert RESET through SW1, ISP and CH340 DTR while both switch enables are HIGH. U8/U10 outputs must fall immediately, VPP must disappear and K1 must return to READ. Confirm D9 limits the positive RESET pulse from DTR release. CE/OE/PGM must become inactive through the pull-ups. Test power-on, brownout and USB disconnection without an EPROM.
6. Test missing frames, bad CRC, wrong image offsets, UART errors, host cancellation and cable loss. VPP must turn off and the relay return to READ. During programming the keepalive timeout is 500 ms and the watchdog is 1 s; hardware RESET gates provide the faster independent cutoff.

Only after recording measurements, assemble-specific calibration and successful fault tests, rebuild with `./firmware/build.ps1 -Commissioned -BandgapMillivolts <calibrated_value>`. Use a spare, correctly erased NM27C512 at 20-30 C for the first write. Check the programmed image with a separate known-good reader. The delivered `dumper_commissioned.hex` is a compile-check artifact with nominal bandgap and is not an approved image for an untested board.

## Operating sequence

Power down USB and VPP before inserting/removing the target or adapter. Populate exactly one target: either U6 or an adapter on J_TARGET. Reconnect USB logic before enabling the external supply. Firmware WRITE first blank-checks the whole device, tests switched VPP with the socket isolated, removes/discharges VPP, selects 6.25 V, then checks VCC and VPP before each programming pulse. It releases MCU data outputs before changing the HCT245 direction. Every byte is verified; the host resends the image for final comparison at 5 V. Failure can leave an EPROM partly programmed; it needs UV erasure before retry.

The current relay selects 5 V or 6.25 V only. Any device requiring another programming VCC, a different pulse polarity or special final verify voltages requires hardware/profile/algorithm changes. J_TARGET and the reference sheets are an adapter basis, not universal socket wiring.
