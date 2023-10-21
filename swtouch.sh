#!/bin/bash
#count=0
#temp=$[$count%2]
if [ $1 -eq 1 ]
then
	#xmodmap .Xmodmap
	xinput --disable 20
	echo "convert to no touchpad"
else
	#xmodmap .XmodmapPre
	xinput --enable 20
	echo "convert to default"
fi
#count=$[$count+1]
# xmodmap .Xmodmap
