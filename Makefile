git_local: 
	read -p 'Суть коммита: ' COMMIT
	git add .
	git commit -am "$COMMIT"

git_remote: 
	git push origin vector
	
git: git_local git_remote
