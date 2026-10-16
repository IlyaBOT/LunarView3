#pragma once
/* Flash this default build for commissioning READ and voltage measurements.
 * Enable WRITE only after the checks in docs/bringup.md, with measured records.
 * Hardware waveform performance is not established by an ERC result.
 */
#ifndef HARDWARE_COMMISSIONED
#define HARDWARE_COMMISSIONED 0
#endif
#ifndef BANDGAP_MV
#define BANDGAP_MV 1100UL
#endif
#define F_CPU 16000000UL
#define UART_BAUD 57600UL
#define FRAME_MAX 128
#define RX_TIMEOUT_MS 500
#ifndef PROGRAMMER_ID
#define PROGRAMMER_ID "Lunar_Writer"
#endif
#ifndef PROGRAMMER_REVISION
#define PROGRAMMER_REVISION 1
#endif
#ifndef PROGRAMMER_VERSION
#define PROGRAMMER_VERSION "1.0.0"
#endif
#define WRITER_STRING_INNER(x) #x
#define WRITER_STRING(x) WRITER_STRING_INNER(x)
