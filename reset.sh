#!/bin/bash
# Simple aliases for the learning data reset tool

case "$1" in
  "status"|"s")
    python reset_learning_data.py status
    ;;
  "all"|"a")
    echo "🚨 This will reset ALL learning data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      python reset_learning_data.py reset-all
    else
      echo "❌ Cancelled"
    fi
    ;;
  "uk"|"UK")
    python reset_learning_data.py reset-jurisdiction "United Kingdom"
    ;;
  "sessions")
    python reset_learning_data.py reset-sessions
    ;;
  "profiles") 
    python reset_learning_data.py reset-profiles
    ;;
  *)
    echo "🔧 Learning Data Reset Shortcuts"
    echo
    echo "Usage: ./reset.sh [command]"
    echo
    echo "Commands:"
    echo "  status, s     Show current status"
    echo "  all, a        Reset everything (with confirmation)"
    echo "  uk, UK        Reset UK jurisdiction only"
    echo "  sessions      Reset learning sessions only"
    echo "  profiles      Reset jurisdiction profiles only"
    echo
    echo "For more options, use: python reset_learning_data.py --help"
    ;;
esac