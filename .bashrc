# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
#force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
	# We have color support; assume it's compliant with Ecma-48
	# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
	# a case would tend to support setf rather than setaf.)
	color_prompt=yes
    else
	color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    ;;
*)
    ;;
esac

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# colored GCC warnings and errors
#export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
    . ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

alias swkey='/home/lucifer/shellProjects/swkey.sh'
alias vscode='/usr/bin/code'
#alias qq='/home/lucifer/shellProjects/qq.sh'
alias bing='/home/lucifer/shellProjects/bing.sh'
alias swkey='/home/lucifer/shellProjects/swkey.sh'
alias swtouch='/home/lucifer/shellProjects/swtouch.sh'
#alias wall='/home/lucifer/shellProjects/wall.sh'
alias bili='/home/lucifer/shellProjects/bilibili.sh'
alias fanyi='/home/lucifer/shellProjects/fanyi.sh'
alias note='/home/lucifer/shellProjects/save.sh'
. /home/lucifer/shellProjects/z/z.sh
alias reboot='/home/lucifer/shellProjects/detect_reboot.sh'
alias poweroff='/home/lucifer/shellProjects/detect_poweroff.sh'
alias setsound='/home/lucifer/shellProjects/lowersound.sh'
alias print_monitor='/home/lucifer/shellProjects/monitor_process &'
alias zotero='/home/lucifer/Applications/Zotero_linux-x86_64/zotero'
alias blender='/home/lucifer/blender-5.0.1-linux-x64/blender'
#alias bat='batcat'
#alias pwd='/home/lucifer/shellProjects/detect_reboot.sh'
#source ~/ros2_humble/install/setup.bash
export PATH=/home/lucifer/.local/bin:$PATH
#export SPARK_HOME=/home/lucifer/spark-3.5.3-bin-hadoop3
#export PATH=$SPARK_HOME/bin:$PATH
#export PATH=/home.lucifer/apache-maven-3.9.9/bin:$PATH
#export PATH=/home/lucifer/shellProjects/detect.sh:$PATH


#export NVM_DIR="$HOME/.nvm"
#[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
#[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
export PATH=$PATH:~/Codes/FlameGraph

export ROS_HOSTNAME=main
export ROS_MASTER_URI=http://main:11311

#. "$HOME/.cargo/env"
. "$HOME/.cargo/env"

#export PATH="$PATH:/opt/nvim-linux-x86_64/bin"

# opencode
export PATH=/home/lucifer/.opencode/bin:$PATH

export PATH="$HOME/.npm-global/bin:$PATH"
export PATH="$(npm prefix -g)/bin:$PATH"

# OpenClaw Completion
#source "/home/lucifer/.openclaw/completions/openclaw.bash"

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
#__conda_setup="$('/home/lucifer/miniconda3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
#if [ $? -eq 0 ]; then
#    eval "$__conda_setup"
#else
#    if [ -f "/home/lucifer/miniconda3/etc/profile.d/conda.sh" ]; then
#        . "/home/lucifer/miniconda3/etc/profile.d/conda.sh"
#    else
#        export PATH="/home/lucifer/miniconda3/bin:$PATH"
#    fi
#fi
#unset __conda_setup
# <<< conda initialize <<<
#conda deactivate
alias rl='source /home/lucifer/shellProjects/activate.sh'
alias rloff='source /home/lucifer/shellProjects/deactivate.sh'
alias reloadwifi='/home/lucifer/shellProjects/reloadwifi.sh'
# ---- 自定义提示符: (env)[lan-ip]/full/path: ----
__prompt_lan_ip() {
  # 取默认路由对应的本机局域网 IP
  ip -4 route get 1.1.1.1 2>/dev/null \
    | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}'
}

__set_rl_prompt() {
  local env_name="${_RL_ENV_NAME:-${CONDA_DEFAULT_ENV:-}}"
  local lan_ip
  lan_ip="$(__prompt_lan_ip)"
  [ -z "$lan_ip" ] && lan_ip="no-ip"

  # 256 色（多数终端都支持）
  local R='\[\e[0m\]'
  local DIM='\[\e[38;5;240m\]'    # 暗灰：括号/分隔
  local ENV='\[\e[38;5;114m\]'    # 柔绿：环境
  local IP='\[\e[38;5;180m\]'     # 浅杏：IP
  local UH='\[\e[38;5;110m\]'     # 雾蓝：user@host
  local PATHC='\[\e[38;5;75m\]'   # 亮蓝：路径
  local PROMPT='\[\e[38;5;245m\]' # 提示符

  if [ -n "$env_name" ] && [ "$env_name" != "base" ]; then
    PS1="${DIM}(${ENV}${env_name}${DIM})[${IP}${lan_ip}${DIM}]${UH}\u@\h${DIM}:${PATHC}${PWD}${PROMPT}\$${R}"
  else
    PS1="${DIM}[${IP}${lan_ip}${DIM}]${UH}\u@\h${DIM}:${PATHC}${PWD}${PROMPT}\$${R}"
  fi
}
# 若已有 PROMPT_COMMAND，追加而不是覆盖
if [[ -n "${PROMPT_COMMAND:-}" ]]; then
  PROMPT_COMMAND="__set_rl_prompt; ${PROMPT_COMMAND}"
else
  PROMPT_COMMAND="__set_rl_prompt"
fi

# >>> unilab completion >>>
if [ -f "/home/lucifer/codes/rl/UniLab/scripts/completions/unilab.bash" ]; then
    source "/home/lucifer/codes/rl/UniLab/scripts/completions/unilab.bash"
fi
# <<< unilab completion <<<
