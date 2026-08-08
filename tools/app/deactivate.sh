#!/usr/bin/env bash
# 用法: source ~/shellProjects/tools/app/deactivate.sh
# 或 alias: rloff

if [ -z "${_RL_ACTIVE:-}" ]; then
  echo "[rl] 当前不在 rl* 环境中"
  return 0 2>/dev/null || exit 0
fi

if [ "${_RL_HAD_LD_LIBRARY_PATH:-0}" = "1" ]; then
  export LD_LIBRARY_PATH="$_RL_OLD_LD_LIBRARY_PATH"
else
  unset LD_LIBRARY_PATH
fi

_prev="${_RL_OLD_CONDA_ENV:-}"
# 若进入前就是某个 rl*，一律 deactivate，避免「退回另一个 rl*」造成假嵌套
case "$_prev" in
  rl*|base|"")
    conda deactivate
    ;;
  *)
    conda activate "$_prev" || conda deactivate
    ;;
esac

unset _RL_ACTIVE _RL_ENV_NAME
unset _RL_OLD_LD_LIBRARY_PATH _RL_HAD_LD_LIBRARY_PATH _RL_OLD_CONDA_ENV
unset _prev

echo "[rl] deactivated (conda=${CONDA_DEFAULT_ENV:-none})"
