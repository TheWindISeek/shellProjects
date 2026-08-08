# shellProjects 工具入口（由 install.py 挂到 ~/.bashrc）
# 改别名只改本文件即可，无需再动 bashrc。

_SHELLPROJECTS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_T="${_SHELLPROJECTS_ROOT}/tools"

# ---- app：日常快捷 ----
alias bing="${_T}/app/bing.sh"
alias bili="${_T}/app/bilibili.sh"
alias fanyi="${_T}/app/fanyi.sh"
alias swkey="${_T}/app/swkey.sh"
alias swtouch="${_T}/app/swtouch.sh"
alias setsound="${_T}/app/lowersound.sh"
alias note="${_T}/app/save.sh"
alias rl="source ${_T}/app/activate.sh"
alias rloff="source ${_T}/app/deactivate.sh"
#alias qq="${_T}/app/qq.sh"

# ---- net：网络 ----
alias reloadwifi="${_T}/net/reloadwifi.sh"
#alias wall="${_T}/net/wall.sh"
#alias gitproxy="${_T}/net/gitproxy.sh"
#alias ipgw="${_T}/net/neu_ipgw.py"

# ---- sys：系统 ----
alias reboot="${_T}/sys/detect_reboot.sh"
alias poweroff="${_T}/sys/detect_poweroff.sh"
alias print_monitor="${_T}/sys/monitor_process &"
#alias killname="${_T}/sys/killname.sh"

# ---- 目录跳转 z ----
if [ -f "${_SHELLPROJECTS_ROOT}/vendor/z/z.sh" ]; then
  # shellcheck disable=SC1091
  . "${_SHELLPROJECTS_ROOT}/vendor/z/z.sh"
else
  echo "[shellProjects] z missing: git clone --depth 1 https://github.com/rupa/z.git ${_SHELLPROJECTS_ROOT}/vendor/z"
fi

# ---- 终端提示符配色 ----
# shellcheck disable=SC1091
. "${_T}/app/prompt.sh"

# ---- UniLab completion（文件不存在则跳过）----
# >>> unilab completion >>>
if [ -f "${HOME}/codes/rl/UniLab/scripts/completions/unilab.bash" ]; then
  # shellcheck disable=SC1091
  . "${HOME}/codes/rl/UniLab/scripts/completions/unilab.bash"
fi
# <<< unilab completion <<<

unset _SHELLPROJECTS_ROOT _T
