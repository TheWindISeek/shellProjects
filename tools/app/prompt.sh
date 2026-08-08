# 自定义提示符: (env)[lan-ip]user@host:full/path$
# 由 shellrc.sh source（tools/app），勿直接写进 ~/.bashrc。

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

# 避免重复 source shellrc 时叠多层 PROMPT_COMMAND
if [ -z "${_SHELLPROJECTS_PROMPT:-}" ]; then
  if [[ -n "${PROMPT_COMMAND:-}" ]]; then
    PROMPT_COMMAND="__set_rl_prompt; ${PROMPT_COMMAND}"
  else
    PROMPT_COMMAND="__set_rl_prompt"
  fi
  _SHELLPROJECTS_PROMPT=1
fi
