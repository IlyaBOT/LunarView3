#ifndef DUMPER_IDENTITY_H
#define DUMPER_IDENTITY_H
/* Override these defines when building another hardware/firmware revision.
 * All identity text is emitted through PSTR, so it stays in flash, not SRAM. */
#ifndef DUMPER_NAME
#define DUMPER_NAME "Lunar Dumper"
#endif
#ifndef DUMPER_REVISION
#define DUMPER_REVISION 1
#endif
#ifndef FIRMWARE_VERSION
#define FIRMWARE_VERSION "1.0.0"
#endif
#ifndef FIRMWARE_BUILD_ID
#define FIRMWARE_BUILD_ID "manual"
#endif
#ifndef FIRMWARE_BUILD_DATE
#define FIRMWARE_BUILD_DATE __DATE__
#endif
#define ID_STRING_INNER(x) #x
#define ID_STRING(x) ID_STRING_INNER(x)
#define DUMPER_IDENTITY DUMPER_NAME " (Rev. " ID_STRING(DUMPER_REVISION) ") | Firmware: v." FIRMWARE_VERSION " (build " FIRMWARE_BUILD_ID ") " FIRMWARE_BUILD_DATE
#endif
