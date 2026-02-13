#!/usr/bin/env bash
# 使用 rsync 将本地 MP4 目录同步到远程 Jellyfin 媒体目录
# 用法: ./sync_mp4_to_remote.sh [远程用户@远程主机]

set -e

# 本地 MP4 目录（项目根目录下的 mp4/）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_DIR="${LOCAL_DIR:-$SCRIPT_DIR/mp4}"
REMOTE_PATH="/share/data/jellyfin/media/jable"

# 远程主机：可通过参数传入，或设置环境变量 REMOTE_HOST
# 例如: REMOTE_HOST="user@192.168.1.100" 或 ./sync_mp4_to_remote.sh user@192.168.1.100
REMOTE_HOST="${1:-${REMOTE_HOST}}"

if [[ -z "$REMOTE_HOST" ]]; then
  echo "错误: 未指定远程主机。" >&2
  echo "用法: $0 用户@主机" >&2
  echo "  或: REMOTE_HOST=用户@主机 $0" >&2
  echo "示例: $0 myuser@192.168.1.100" >&2
  exit 1
fi

if [[ ! -d "$LOCAL_DIR" ]]; then
  echo "错误: 本地目录不存在: $LOCAL_DIR" >&2
  exit 1
fi

echo "同步: $LOCAL_DIR/ -> ${REMOTE_HOST}:${REMOTE_PATH}/"
# -P = --partial --progress：保留未传完的文件，下次可断点续传
rsync -avz -P \
  "$LOCAL_DIR/" \
  "${REMOTE_HOST}:${REMOTE_PATH}/"

echo "同步完成。"
