echo "start to save obsidian projects"
cd ~/obsidian-projects
git add .
git commit -m $1
git push origin master
cd ~
