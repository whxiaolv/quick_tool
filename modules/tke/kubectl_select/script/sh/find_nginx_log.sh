#!/bin/sh

# 用法案例
# ./find_nginx_log.sh -date=2026-03-19 -dir=/letv/logs/nginx
# ./find_nginx_log.sh -dir=/letv/logs/nginx -date=2026-03-19
# ./find_nginx_log.sh -date=20260319
# ./find_nginx_log.sh -dir=/letv/logs
# ./find_nginx_log.sh

set -eu

# ==================== 用法 ====================
usage() {
  echo "用法：$0 [-dir=日志目录] [-date=日期]"
  echo "示例："
  echo "  $0                                    # 默认：今天 + /letv/logs"
  echo "  $0 -date=2026-03-19                   # 指定日期"
  echo "  $0 -dir=/letv/logs/nginx              # 指定目录"
  echo "  $0 -dir=/letv/logs/nginx -date=20260319"
  echo "  $0 -date=2026-03-19 -dir=/letv/logs/nginx  # 顺序随意"
  exit 1
}

# ==================== 解析 -dir=xxx -date=xxx 参数 ====================
DATE_DASH=""
DATE_NUM=""
USER_LOG_DIR=""
IS_TODAY=1

for arg in "$@"; do
  case "$arg" in
    -dir=*)
      USER_LOG_DIR="${arg#-dir=}"
      ;;
    -date=*)
      DATE_INPUT="${arg#-date=}"
      if echo "$DATE_INPUT" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
        DATE_DASH="$DATE_INPUT"
        DATE_NUM=$(echo "$DATE_INPUT" | tr -d '-')
      elif echo "$DATE_INPUT" | grep -Eq '^[0-9]{8}$'; then
        DATE_NUM="$DATE_INPUT"
        DATE_DASH=$(echo "$DATE_INPUT" | sed 's/^\(....\)\(..\)\(..\)$/\1-\2-\3/')
      else
        echo "❌ 日期格式错误：$DATE_INPUT"
        exit 1
      fi
      IS_TODAY=0
      ;;
    *)
      echo "❌ 未知参数：$arg"
      usage
      exit 1
      ;;
  esac
done

# 未传日期 → 默认今天
if [ -z "$DATE_DASH" ]; then
  DATE_DASH=$(date +%Y-%m-%d)
  DATE_NUM=$(date +%Y%m%d)
  IS_TODAY=1
fi

# ==================== 日志查找函数 ====================
search_log() {
  local target_dir="$1"
  if [ ! -d "$target_dir" ]; then
    return 1
  fi

  # 今天优先：access.log
  if [ "$IS_TODAY" -eq 1 ]; then
    if [ -f "${target_dir}/access.log" ]; then
      echo "${target_dir}/access.log"
      return 0
    fi
  fi

  # 带日期匹配
  local log
  log=$(ls -1 "${target_dir}"/access.log*"${DATE_DASH}"* \
            "${target_dir}"/access.log*"${DATE_NUM}"* 2>/dev/null | head -n1)
  if [ -n "$log" ] && [ -f "$log" ]; then
    echo "$log"
    return 0
  fi

  return 1
}

# ==================== 按优先级查找 ====================
# 1. 用户指定目录
if [ -n "$USER_LOG_DIR" ]; then
  LOG_FILE=$(search_log "$USER_LOG_DIR")
  if [ -n "$LOG_FILE" ]; then
    echo "$LOG_FILE"
    exit 0
  fi
fi

# 2. 默认路径
LOG_FILE=$(search_log "/letv/logs")
if [ -n "$LOG_FILE" ]; then
  echo "$LOG_FILE"
  exit 0
fi

LOG_FILE=$(search_log "/letv/logs/nginx")
if [ -n "$LOG_FILE" ]; then
  echo "$LOG_FILE"
  exit 0
fi

# ==================== 从 Nginx 进程取配置 ====================
get_log_dir_from_conf() {
  local conf="$1"
  if [ ! -f "$conf" ]; then return 1; fi
  local path
  path=$(grep -E '^[ \t]*access_log' "$conf" | head -n1 | awk '{print $2}' | sed 's/;$//')
  if [ -n "$path" ]; then
    dirname "$path"
  fi
}

NGINX_CONF=$(ps aux | grep nginx | grep master | grep -v grep | sed -n 's/.*-c \([^ ]*\).*/\1/p' | head -n1)
if [ -n "$NGINX_CONF" ]; then
  LOG_DIR=$(get_log_dir_from_conf "$NGINX_CONF" || true)
  if [ -n "$LOG_DIR" ]; then
    LOG_FILE=$(search_log "$LOG_DIR")
    if [ -n "$LOG_FILE" ]; then
      echo "$LOG_FILE"
      exit 0
    fi
  fi
fi

# ==================== find 查找配置 ====================
NGINX_CONF=$(find /etc /letv /usr /opt -name nginx.conf 2>/dev/null | head -n1)
if [ -n "$NGINX_CONF" ]; then
  LOG_DIR=$(get_log_dir_from_conf "$NGINX_CONF" || true)
  if [ -n "$LOG_DIR" ]; then
    LOG_FILE=$(search_log "$LOG_DIR")
    if [ -n "$LOG_FILE" ]; then
      echo "$LOG_FILE"
      exit 0
    fi
  fi
fi

# ==================== 失败 ====================
echo ""
exit 1