# network setting with proxy
if [ $1 -eq 1 ]
then
	gsettings set org.gnome.system.proxy mode 'manual'
	currentPath = $(pwd)
	cd ~/clash
	./clash &
	echo "clash start!"
	cd $currentPath
	echo "convert to manual"
else
	gsettings set org.gnome.system.proxy mode 'none'
	killall clash
	echo "convert to disabled"
	env | grep proxy
fi
