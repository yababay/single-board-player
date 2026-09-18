# Переменные путей
PROJECT_NAME = single-board-player
BUILD_DIR = $(HOME)/deb_build/$(PROJECT_NAME)
PROJECT_DIR = $(shell pwd)
MUSIC_DIR = $(HOME)/Music
BACKUP_DIR = $(HOME)/Backups

.PHONY: db_backup deb_clean deb_prepare deb_build deb

git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin vector

git: git_local git_remote

psql:
	psql -d player

db_backup:
	# Создание дампа базы данных player
	# Используйте эту команду для создания резервной копии базы данных
	pg_dump -h localhost -U mabel -F p --clean -b -f $(MUSIC)/player_semantic_db.sql player

db_restore:
	# Восстановление базы данных из дампа
	# Используйте эту команду, если у вас есть дамп базы данных player.dump
	psql -h localhost -U postgres -d player -f $(MUSIC)/player_semantic_db.sql

model_backup:
	# Создание резервной копии модели
	# Используйте эту команду для создания резервной копии модели
	tar -cvf $(BACKUP_DIR)/$(PROJECT_NAME)-models.tar -C scripts/ models

# 1. Очистка старых следов сборки
clean:
	rm -rf $(BUILD_DIR)
	rm -f $(HOME)/deb_build/single-board-player.deb

# 2. Создание структуры папок и копирование файлов
prepare: db_backup clean
	mkdir -p $(BUILD_DIR)/DEBIAN
	mkdir -p $(BUILD_DIR)/usr/share/single-board-player/scripts
	mkdir -p $(BUILD_DIR)/etc/systemd/user
	mkdir -p $(BUILD_DIR)/var/lib/mpd/playlists
	
	# Копируем управляющие манифесты (которые мы подготовим ниже)
	cp $(PROJECT_DIR)/DEBIAN/control $(BUILD_DIR)/DEBIAN/
	cp $(PROJECT_DIR)/DEBIAN/postinst $(BUILD_DIR)/DEBIAN/
	chmod +x $(BUILD_DIR)/DEBIAN/postinst
	
	# Копируем наши отлаженные рабочие скрипты пульта
	cp $(PROJECT_DIR)/scripts/local-search-server.py $(BUILD_DIR)/usr/share/single-board-player/scripts/
	cp $(PROJECT_DIR)/scripts/voice-assistant.py $(BUILD_DIR)/usr/share/single-board-player/scripts/
	cp $(PROJECT_DIR)/scripts/playlist_checker.py $(BUILD_DIR)/usr/share/single-board-player/scripts/
	cp $(PROJECT_DIR)/scripts/query_normalizer.py $(BUILD_DIR)/usr/share/single-board-player/scripts/
	cp $(PROJECT_DIR)/scripts/yaml2db.py $(BUILD_DIR)/usr/share/single-board-player/scripts/
	
	# Копируем плейлисты и свежий 21-мегабайтный дамп СУБД для автодеплоя
	cp $(MUSIC_DIR)/*.m3u $(BUILD_DIR)/var/lib/mpd/playlists
	cp $(MUSIC_DIR)/player_semantic_db.sql $(BUILD_DIR)/usr/share/single-board-player/
	
	# Копируем systemd-юниты
	cp $(PROJECT_DIR)/DEBIAN/music-ai-search.service $(BUILD_DIR)/etc/systemd/user/
	cp $(PROJECT_DIR)/DEBIAN/music-voice-assistant.service $(BUILD_DIR)/etc/systemd/user/

# 3. Финальная компиляция пакета утилитой dpkg-deb
build:
	dpkg-deb --build $(BUILD_DIR)
	mv $(HOME)/deb_build/single-board-player.deb $(PROJECT_DIR)/
	@echo "========================================================="
	@echo "🎉 Успех! Пакет single-board-player.deb собран в корне проекта."
	@echo "========================================================="

# Главная сквозная команда сборки
all: deb_prepare deb_build
