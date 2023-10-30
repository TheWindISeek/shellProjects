#!/bin/bash
#count=0
#temp=$[$count%2]
touchpad=$(xinput | grep Touch | cut -d '=' -f 2 | cut -d '[' -f 1)
if [ $1 -eq 1 ]
then
	#xmodmap .Xmodmap
	xinput --disable $touchpad
	echo "convert to no touchpad"
else
	#xmodmap .XmodmapPre
	xinput --enable $touchpad
	echo "convert to default"
fi
#count=$[$count+1]
# xmodmap .Xmodmap
