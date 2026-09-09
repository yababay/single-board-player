git_local: 
	read -p 'Суть коммита: ' COMMIT
	git add .
	git commit -am "$COMMIT"

git_remote: 
	git push origin vector

cp_m3u2yaml:
	cp /usr/local/bin/m3u2yaml scripts/m3u2yaml.sh
	
git: cp_m3u2yaml git_local git_remote
