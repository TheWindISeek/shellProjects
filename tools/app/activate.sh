#!/usr/bin/env bash
# 用法:
#   source ~/shellProjects/tools/app/activate.sh           # -> conda env: rl
#   source ~/shellProjects/tools/app/activate.sh unilab    # -> conda env: rlunilab
#   source ~/shellProjects/tools/app/activate.sh deepmimic # -> conda env: rldeepmimic
# 或 alias: rl / rl unilab / rl deepmimic

_suffix="${1:-}"
if [ -n "$_suffix" ]; then
  _target="rl${_suffix}"
else
  _target="rl"
fi

# 已在同一个环境里
if [ "${_RL_ACTIVE:-}" = "1" ] && [ "${CONDA_DEFAULT_ENV:-}" = "$_target" ]; then
  echo "[rl] 已经在 ${_target} 中"
  unset _suffix _target
  return 0 2>/dev/null || exit 0
fi

# 已由 rl 管理，禁止嵌套/切换（先 rloff）
if [ "${_RL_ACTIVE:-}" = "1" ] && [ "${CONDA_DEFAULT_ENV:-}" != "$_target" ]; then
  echo "[rl] 已在 ${_RL_ENV_NAME:-$CONDA_DEFAULT_ENV} 中，请先 rloff 再切换到 ${_target}" >&2
  unset _suffix _target
  return 1 2>/dev/null || exit 1
fi

# 当前 conda 已是某个 rl*（含裸 conda activate），禁止再嵌套进另一个
case "${CONDA_DEFAULT_ENV:-}" in
  rl*)
    if [ "${CONDA_DEFAULT_ENV}" != "$_target" ]; then
      echo "[rl] 当前已在 ${CONDA_DEFAULT_ENV}，请先 rloff 或 conda deactivate，再进入 ${_target}" >&2
      unset _suffix _target
      return 1 2>/dev/null || exit 1
    fi
    ;;
esac

if ! command -v conda >/dev/null 2>&1; then
  if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck disable=SC1091
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
  else
    echo "[rl] 找不到 conda" >&2
    unset _suffix _target
    return 1 2>/dev/null || exit 1
  fi
fi

# 第一次进入时备份「原始」LD_LIBRARY_PATH；切换环境时不重复备份
if [ -z "${_RL_ACTIVE:-}" ]; then
  if [ -n "${LD_LIBRARY_PATH+x}" ]; then
    export _RL_OLD_LD_LIBRARY_PATH="$LD_LIBRARY_PATH"
    export _RL_HAD_LD_LIBRARY_PATH=1
  else
    unset _RL_OLD_LD_LIBRARY_PATH
    export _RL_HAD_LD_LIBRARY_PATH=0
  fi
  export _RL_OLD_CONDA_ENV="${CONDA_DEFAULT_ENV:-}"
fi

conda activate "$_target" || {
  echo "[rl] conda activate ${_target} 失败（先 conda create -n ${_target} ...）" >&2
  unset _suffix _target
  return 1 2>/dev/null || exit 1
}

# 基于备份重建，避免多次 activate 把路径叠很多层
if [ "${_RL_HAD_LD_LIBRARY_PATH:-0}" = "1" ]; then
  export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib:${_RL_OLD_LD_LIBRARY_PATH}"
else
  export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib"
fi

export _RL_ACTIVE=1
export _RL_ENV_NAME="$_target"

echo "[rl] activated: conda=${CONDA_DEFAULT_ENV}"
echo "[rl] LD_LIBRARY_PATH += ${CONDA_PREFIX}/lib"

unset _suffix _target
