#!/usr/bin/env bash
# Shortcut: send a task to both brains in parallel.
# Usage: ./both.sh "review PR #42 from all angles"
exec "$(dirname "$0")/trigger.sh" both "$@"
