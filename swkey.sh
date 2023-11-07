#!/bin/bash
#count=0
#temp=$[$count%2]
if [ $1 -eq 1 ]
then
	xmodmap ~/shellProjects/.Xmodmap
	echo "apply change"
else
	xmodmap ~/shellProjects/.XmodmapPre
	echo "convert to default"
fi
#count=$[$count+1]
# xmodmap .Xmodmap
