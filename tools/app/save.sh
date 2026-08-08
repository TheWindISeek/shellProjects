if [ $1 -eq 1 ]
then
    echo "start to save obsidian projects"
    cd ~/obsidian-projects
    git add .
    git commit -m $2
    git push origin master
    # cd ~
else
    echo "git pull from remote"
    cd ~/obsidian-projects
    git pull
    git log
fi
