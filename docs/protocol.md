# Lunar Writer — UART protocol v1

57600 baud, 8 data bits, no parity, 1 stop bit; no flow control. Commands are ASCII with LF (optional CR ignored). The host uses DTR to reset the board on open and close. A command always begins from inactive controls; no operation relies on an Arduino bootloader.

| Command | Response / transfer |
|---|---|
| INFO | `INFO protocol=1 profile_hash=<16 hex chars> commissioned=0/1 reset=<MCUSR byte> device=Lunar_Writer revision=1 firmware=1.0.0` |
| LIST | Canonical name, byte size, read flag and profile-program flag per row; `END` |
| VOLTAGES | `VOLTAGES logic_mv=... target_mv=... vpp_sw_mv=... vpp_in=unmeasured` |
| READ name | `DATA n\n`, exactly n raw bytes, LF, `OK CCCC\n` |
| VERIFY name | `READY 128\n`, framed image input with ACKs, then `OK CCCC\n` |
| WRITE name | Preflight/blank check, `READY 128\n`, programming input with ACKs; `VERIFY_READY 128\n`, same image again for final 5 V comparison, then `OK CCCC\n` |

Error responses start with `ERR ` and a reason, after VPP is disabled and the relay returns to READ. Typical reasons include READ_VOLTAGE, PROGRAM_PROFILE_DISABLED, HARDWARE_NOT_COMMISSIONED, PROGRAM_VOLTAGE, NOT_ERASED and a transfer/verify failure. LIST's programming flag describes the profile; check INFO's commissioned flag as well.

## Binary input frames

`A5 5A | offset:u32 LE | length:u16 LE | data:length | crc:u16 LE`

Length is 1-128 and offset must equal the next expected byte. CRC16/CCITT-FALSE starts at FFFF, polynomial 1021, no reflection or final XOR; it covers offset, length and data, excluding magic. The known check vector `123456789` gives 29B1. Each accepted block returns `ACK <next offset>\n`. The final ASCII CRC covers all image bytes and must match the host. READ has exact framing and whole-image CRC; the host creates its output file only after validation and refuses to overwrite an existing dump.

While waiting for a programming ACK or preflight readiness, the host sends byte 06 every 100 ms. Firmware accepts this keepalive only between frames and during bounded programming/blank-check work. It has no special meaning inside a frame's payload. Received bytes have a 500 ms timeout; UART framing/overrun/parity errors abort. Watchdog is enabled for all work, with 1 s timeout. VPP is OFF while waiting for a frame; it can be present only during bounded preflight or per-byte programming work. On host cancellation the tool also generates a hardware RESET edge in its finally block.

VOLTAGES makes the hardware safe and measures VPP_SW, not the external input directly. WRITE preflight measures the external supply through Q3/Q7 with K1 still in READ, isolating the target. Do not interpret the normal 0 V VPP_SW reported before WRITE as an absent external supply. The waveform checks in bringup.md remain necessary: firmware ADC checks cannot detect a fast spike before it reaches the device.

The simulator tests cover framing, CRC, hash mismatch, partial serial reads, errors, keepalive, refusal of unsupported operations and cleanup. They do not emulate physical AVR timing, relay contacts or EPROM programming.
