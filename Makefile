# Переменные путей
PROJECT_NAME = single-board-player
PROJECT_DIR  = $(shell pwd)
HOME_DIR     = $${HOME}
BUILD_DIR    = $(HOME_DIR)/deb_build/$(PROJECT_NAME)
MUSIC_DIR    = $(HOME_DIR)/Music
BACKUP_DIR   = $(HOME_DIR)/Backups

.PHONY: db_backup clean prepare build deb git psql db_restore model_backup catalog

# Главная сквозная команда сборки
all: prepare build

deploy_service:
	scp scripts/music-ai-search.py music:/usr/share/schulbert
	scp DEBIAN/music-ai-search.service music:/home/player/.config/systemd/user
	ssh music "systemctl --user daemon-reload && systemctl --user restart music-ai-search.service"

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
	# 🌟 СУПЕР-ХАК СТАРОЙ ШКОЛЫ:
	# Читаем дамп, на лету заменяем 'mabel' на 'player' и безболезненно скармливаем Postgres
	# Флаг --clean в дампе сам пересоздаст таблицы, а триггеры подхватятся автоматически
	sed 's/OWNER TO mabel/OWNER TO player/g; s/TO mabel/TO player/g' $(MUSIC_DIR)/player_semantic_db.sql | psql -h localhost -U player -d player
	

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
	mkdir -p $(BUILD_DIR)/usr/share/single-board-player/scripts
	mkdir -p $(BUILD_DIR)/etc/systemd/user
	mkdir -p $(BUILD_DIR)/var/lib/mpd/playlists
	mkdir -p $(BUILD_DIR)/usr/local/bin

	# Создаем системную директорию настроек WirePlumber внутри пакета
	mkdir -p $(BUILD_DIR)/etc/wireplumber/wireplumber.conf.d
	
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
	cp $(PROJECT_DIR)/scripts/user-init-audio.sh $(BUILD_DIR)/usr/share/single-board-player/scripts
	
	# Копируем плейлисты
	cp $(MUSIC_DIR)/*.m3u $(BUILD_DIR)/var/lib/mpd/playlists
	
	# Копируем systemd-юниты
	cp $(PROJECT_DIR)/DEBIAN/music-ai-search.service $(BUILD_DIR)/etc/systemd/user/
	cp $(PROJECT_DIR)/DEBIAN/music-voice-assistant.service $(BUILD_DIR)/etc/systemd/user/
	
	# Записываем вашу блюз/джаз находку, отключающую блокировку logind для безголового сервера!
	echo 'wireplumber.profiles = { main = { monitor.bluez.seat-monitoring = disabled } }' > $(BUILD_DIR)/etc/wireplumber/wireplumber.conf.d/99-headless-bluetooth.conf

## 3. Финальная компиляция пакета утилитой dpkg-deb
build:
	dpkg-deb --build $(BUILD_DIR)
	mv $(HOME)/deb_build/single-board-player.deb $(PROJECT_DIR)/
	@echo "========================================================="
	@echo "🎉 Успех! Пакет single-board-player.deb собран в корне проекта."
	@echo "========================================================="

# Генерация красивого печатного каталога всей фонотеки
catalog:
	@echo "📄 Экспорт каталога фонотеки в catalog.md..."
	@psql -h localhost -U player -d player -t -A -c " \
		SELECT case \
			when pl_break.new_cat = 1000 then E'\n# Классическая музыка\n' \
			when pl_break.new_cat = 2000 then E'\n# Рок-музыка\n' \
			when pl_break.new_cat = 3000 then E'\n# Джаз\n' \
			when pl_break.new_cat = 4000 then E'\n# Блюз\n' \
			else '' \
		end || E'\n## ' || t.playlist_number || '-' || lower(regexp_replace(coalesce(t.album, 'playlist'), '[^a-zA-Z0-9]+', '-', 'g')) || E'\n\n' || \
		string_agg('* ' || t.artist || ' - ' || t.title, E'\n' order by t.track_number asc) \
		FROM tracks t \
		JOIN ( \
			SELECT playlist_number, \
			case when (playlist_number / 1000) * 1000 <> lag((playlist_number / 1000) * 1000, 1, 0) over (order by playlist_number) \
			then (playlist_number / 1000) * 1000 else 0 end as new_cat \
			FROM (SELECT DISTINCT playlist_number FROM tracks WHERE playlist_number >= 1000) distinct_pl \
		) pl_break ON t.playlist_number = pl_break.playlist_number \
		GROUP BY t.playlist_number, pl_break.new_cat \
		ORDER BY t.playlist_number ASC;" > docs/catalog.md
	@echo "✅ Каталог успешно сохранен в файл catalog.md"

