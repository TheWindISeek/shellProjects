#!/bin/bash
_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$1" -eq 1 ]; then
	xmodmap "${_DIR}/.Xmodmap"
	echo "apply change"
else
	xmodmap "${_DIR}/.XmodmapPre"
	echo "convert to default"
fi
unset _DIR
