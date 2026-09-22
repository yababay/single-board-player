#!/bin/bash
set -e

echo "🎵 [Аудио-Инит]: Создание символических ссылок на музыку и плейлисты..."
ln -sf /var/lib/mpd/music/ ~/Музыка
ln -sf /var/lib/mpd/playlists/ ~/Плейлисты

echo "🎵 [Аудио-Инит]: Создание локальной структуры папок для MPD в пространстве пользователя..."
mkdir -p ~/.config/mpd
mkdir -p ~/.local/share/mpd
mkdir -p ~/.local/share/mpd/playlists
touch ~/.local/share/mpd/database
touch ~/.local/share/mpd/state
touch ~/.local/share/mpd/pid
touch ~/.local/share/mpd/log

echo "🎵 [Аудио-Инит]: Запись пользовательского файла конфигурации ~/.config/mpd/mpd.conf..."
cat << 'EOF' > ~/.config/mpd/mpd.conf
# Пути к файлам данных (все внутри домашней папки)
music_directory    "~/Музыка"
playlist_directory "~/Плейлисты"
db_file            "~/.local/share/mpd/database"
log_file           "~/.local/share/mpd/log"
pid_file           "~/.local/share/mpd/pid"
state_file         "~/.local/share/mpd/state"
sticker_file       "~/.local/share/mpd/sticker.sql"

# Настройки сети
bind_to_address    "127.0.0.1"
port               "6600"

# АУДИОВЫХОД: Вещание в пользовательский сокет PipeWire
audio_output {
        type            "pulse"
        name            "PipeWire Sound Server"
}
EOF

echo "🎵 [Аудио-Инит]: Активация и запуск пользовательских служб PipeWire и MPD..."
# Перезагружаем конфигурацию пользовательского systemd на всякий случай
systemctl --user daemon-reload

# Включаем и принудительно стартуем весь музыкальный тракт
systemctl --user enable pipewire.service wireplumber.service pipewire-pulse.service mpd.service
systemctl --user start pipewire.service wireplumber.service pipewire-pulse.service mpd.service

# Обновляем базу треков плеера
mpc update

echo "✅ [Аудио-Инит]: Музыкальный тракт пользователя полностью настроен и запущен!"
echo "Теперь вы можете включить вашу Bluetooth-колонку и выполнить сопряжение через bluetoothctl."

