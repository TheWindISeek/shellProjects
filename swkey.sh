#!/bin/bash
#count=0
#temp=$[$count%2]
if [ $1 -eq 1 ]
then
	xmodmap ~/.Xmodmap
	echo "apply change"
else
	xmodmap ~/.XmodmapPre
	echo "convert to default"
fi
#count=$[$count+1]
# xmodmap .Xmodmap
