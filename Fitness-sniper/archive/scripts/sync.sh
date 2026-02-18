#!/bin/bash
# Bi-directional sync between MacBook and Harbor for class-sniper project
# Usage: ./sync.sh [push|pull]

REMOTE="Andess-Mac-mini.local"
LOCAL_DIR="/Users/andeslee/Documents/cursor-projects/class-sniper"
REMOTE_DIR="~/Documents/cursor-projects/class-sniper"
EXCLUDES="--exclude='.git' --exclude='node_modules' --exclude='.DS_Store'"

case "$1" in
  push)
    echo "Pushing to Harbor..."
    rsync -av --update $EXCLUDES "$LOCAL_DIR/" "$REMOTE:$REMOTE_DIR/"
    ;;
  pull)
    echo "Pulling from Harbor..."
    rsync -av --update $EXCLUDES "$REMOTE:$REMOTE_DIR/" "$LOCAL_DIR/"
    ;;
  *)
    echo "Usage: ./sync.sh [push|pull]"
    echo "  push - Send local changes to Harbor"
    echo "  pull - Get Harbor's changes to local"
    ;;
esac
