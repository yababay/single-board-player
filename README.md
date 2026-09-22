# Инструкция по развертыванию ИИ-медиаплеера на MSI Cubi (Debian 13)

### Шаг 1. Установка пакета
Соберите пакет на машине разработки командой `make deb` и перенесите файл `single-board-player.deb` на Cubi. Установите его:
```bash
sudo apt install ./single-board-player.deb
```
*Система сама установит PostgreSQL, PipeWire, создаст конфиг отключения seat-monitoring и настроит multi-user.target.*

### Шаг 2. Перезагрузка (Рекомендовано)
```bash
sudo reboot
```

### Шаг 3. Настройка пользовательского аудио-тракта
Зайдите на Cubi под пользователем `player` и запустите скрипт инициализации:
```bash
/usr/share/single-board-player/scripts/user-init-audio.sh
```

### Шаг 4. Инициализация базы данных и моделей (Финальный аккорд)
Восстановите дамп вашей PostgreSQL и положите ИИ-модели (`models/multilingual-e5-large` и `models/vosk-model-small-ru`) в корень директории `/usr/share/single-board-player/models/`.

