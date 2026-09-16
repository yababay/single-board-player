#!/bin/bash

# Не забудьте установить метку MUSIC на флешку командой
# sudo mlabel -i /dev/sda1 ::MUSIC

PORTABLE="/media/mabel/MUSIC"

if [ ! -d "$PORTABLE" ]; then
	echo 'Не забудьте установить метку MUSIC'
	echo 'на флешку для проигрывателя командой'
	echo 'sudo mlabel -i /dev/sda1 ::MUSIC'
	exit 1
else
	# Создаём каталог
	SHUFFLE_DIR=".shuffle"
	rm -rf   "$SHUFFLE_DIR"
	mkdir -p "$SHUFFLE_DIR"

	# Находим все MP3 и создаём символические ссылки с UUID-именами
	find . \( -name '*.mp3' -o -name '*.flac' -o -name '*.wav' -o -name '*.MP3' -o -name '*.WAV' \) -type f | while read -r file; do
	    # Генерируем UUID (быстрее через /proc)
	    uuid=$(cat /proc/sys/kernel/random/uuid)
	    # echo $uuid
	    # Убираем начальные ./ из пути
	    rel_path="${file#./}"
	    
	    # Создаём ссылку с относительным путём
	    ln -s "../$rel_path" "$SHUFFLE_DIR/${uuid}.mp3"
	done

	PLAYLIST="`pwd | egrep -o '[^\/]+$'`"
	echo Начинаем синхронизацию плейлиста $PLAYLIST…
	TARGET_DIR="$PORTABLE/$PLAYLIST"
	mkdir -p "$TARGET_DIR"
	rsync -rltDv --copy-links --omit-dir-times "$SHUFFLE_DIR/" "$TARGET_DIR/"
	rm -rf   "$SHUFFLE_DIR"
	echo Успешно скопировано `ls -1 $TARGET_DIR | wc -l` файлов.
fi

