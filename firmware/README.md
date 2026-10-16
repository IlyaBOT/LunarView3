# Прошивки Lunar Dumper и Lunar Writer

**Lunar Dumper**: [lite/](lite/README.md), готовый `lite/build/dumper_lite.hex`, 115200 бод, строковый протокол LITE2. Название платы/прошивки теперь Lunar Dumper; старые технические имена папки и HEX сохранены.

**Lunar Writer**: `main.c`, `config.h`, `profiles.h`, `build.ps1`. Сборка `powershell -File firmware/build.ps1` создаёт `writer_safe.hex` и `writer_safe.elf`, 57600 бод, протокол Stage 2 v1. INFO содержит `device=Lunar_Writer revision=1 firmware=1.0.0`; DEFINE доступны в `config.h`. Сборка занимает 4598 байт Flash / 241 байт SRAM. В стандартной прошивке HARDWARE_COMMISSIONED=0, WRITE заблокирована до стендовой проверки.

Силовая часть новой платы описана в [Lunar-Writer/README.md](../Lunar-Writer/README.md). Устаревшие `dumper_safe.*`/`dumper_commissioned.*` удалены; новую сборку следует брать из результата текущего build.ps1. Прошивки устройств имеют разные GPIO и протоколы. LunarView 3 пока обслуживает Lunar Dumper; для Writer существует `tools/eprom_tool.py`.

## RGB

Общая логика цветов — `status_core.h`. Dumper использует PB0/PB1/PD2; Writer — Q4/Q5/Q6 третьего 74HC595. Общий анод, LOW включает канал. READ/VERIFY — зелёный, WRITE — фиолетовый (R+B), 500 мс включены / 500 мс выключены. Подключённое ожидание — янтарный, начальное состояние — красный. INFO в Writer переводит индикацию в подключённое ожидание. В Dumper записи нет. В Writer обновление RGB сохраняет адрес и выполняется вне активного импульса программирования; ISR не переключает защёлку.
