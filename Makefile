git_local: 
	read -p 'Суть коммита: ' COMMIT
	git add .
	git commit -am "$COMMIT"

git_remote: 
	git push origin vector

cp_m3u2yaml:
	cp /usr/local/bin/m3u2yaml scripts/m3u2yaml.sh
	
git: cp_m3u2yaml git_local git_remote

run_model:
	python3 scripts/local-search-server.py

sql:
	psql -U mabel -d player

db_restore:
	# Восстановление базы данных из дампа
	# Используйте эту команду, если у вас есть дамп базы данных player.dump
	psql -h localhost -U postgres -d player -f ~/Music/player_semantic_db.sql

db_backup:
	# Создание дампа базы данных player
	# Используйте эту команду для создания резервной копии базы данных
	./scripts/db-backup.sh	
