# network setting with proxy
if [ $1 -eq 1 ]
then
	git config --global http.proxy 127.0.0.1:7899
	git config --global https.proxy 127.0.0.1:7899
#	git config --list
	git config --global --get http.proxy
	git config --global --get https.proxy
	echo "git set proxy"
else
	git config --global --unset http.proxy
	git config --gloabl --unset https.proxy
#	git config --list
	git config --global --get http.proxy
	git config --global --get https.proxy
	echo "git unset proxy"
fi
