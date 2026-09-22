# Переменные путей
PROJECT_NAME = single-board-player
PROJECT_DIR  = $(shell pwd)
HOME_DIR     = $${HOME}
BUILD_DIR    = $(HOME_DIR)/deb_build/$(PROJECT_NAME)
MUSIC_DIR    = $(HOME_DIR)/Music
BACKUP_DIR   = $(HOME_DIR)/Backups

.PHONY: db_backup clean prepare build deb git psql db_restore model_backup

# Главная сквозная команда сборки
all: prepare build

# Работа с репозиторием
git_local: 
	git add .
	git commit -a

git_remote: 
	git push origin vector

git: git_local git_remote

# Работа с базой данных
psql:
	psql -d player -U player

db_backup:
	# 🌟 СИНХРОНИЗИРОВАНО: Работаем от имени пользователя player
	pg_dump -h localhost -U player -F p --clean -b -f "$(MUSIC_DIR)/player_semantic_db.sql" player

db_restore:
	psql -h localhost -U player -d player -f $(MUSIC_DIR)/player_semantic_db.sql

model_backup:
	# 🌟 СИНХРОНИЗИРОВАНО: Архивация папки models на один уровень выше scripts
	tar -cvf $(BACKUP_DIR)/$(PROJECT_NAME)-models.tar models/

# Сборка
## 1. Очистка старых следов сборки
clean:
	rm -rf $(BUILD_DIR)
	rm -f $(HOME)/deb_build/single-board-player.deb

## 2. Создание структуры папок и копирование файлов
prepare: db_backup clean
	mkdir -p $(BUILD_DIR)/DEBIAN
	mkdir -p $(BUILD_DIR)/usr/share/single-board-player
	mkdir -p $(BUILD_DIR)/etc/systemd/user
	mkdir -p $(BUILD_DIR)/var/lib/mpd/playlists
	mkdir -p $(BUILD_DIR)/usr/local/bin
	
	# Копируем управляющие манифесты
	cp $(PROJECT_DIR)/DEBIAN/control $(BUILD_DIR)/DEBIAN/
	cp $(PROJECT_DIR)/DEBIAN/postinst $(BUILD_DIR)/DEBIAN/
	chmod +x $(BUILD_DIR)/DEBIAN/postinst
	
	# Копируем наши отлаженные рабочие скрипты пульта (ПРЯМО В КОРЕНЬ ПАКЕТА)
	cp $(PROJECT_DIR)/scripts/music-ai-search.py $(BUILD_DIR)/usr/share/single-board-player/
	cp $(PROJECT_DIR)/scripts/music-voice-assistant.py $(BUILD_DIR)/usr/share/single-board-player/
	cp $(PROJECT_DIR)/scripts/playlist_checker.py $(BUILD_DIR)/usr/share/single-board-player/
	cp $(PROJECT_DIR)/scripts/query_normalizer.py $(BUILD_DIR)/usr/share/single-board-player/
	cp $(PROJECT_DIR)/requirements.txt $(BUILD_DIR)/usr/share/single-board-player/
	cp $(PROJECT_DIR)/scripts/yaml2rag.py $(BUILD_DIR)/usr/local/bin/yaml2rag
	
	# Копируем плейлисты
	cp $(MUSIC_DIR)/*.m3u $(BUILD_DIR)/var/lib/mpd/playlists
	
	# Копируем systemd-юниты
	cp $(PROJECT_DIR)/DEBIAN/music-ai-search.service $(BUILD_DIR)/etc/systemd/user/
	cp $(PROJECT_DIR)/DEBIAN/music-voice-assistant.service $(BUILD_DIR)/etc/systemd/user/

## 3. Финальная компиляция пакета утилитой dpkg-deb
build:
	dpkg-deb --build $(BUILD_DIR)
	mv $(HOME)/deb_build/single-board-player.deb $(PROJECT_DIR)/
	@echo "========================================================="
	@echo "🎉 Успех! Пакет single-board-player.deb собран в корне проекта."
	@echo "========================================================="

