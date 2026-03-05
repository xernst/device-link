#!/usr/bin/env bash
# Shortcut: send a task to the right brain.
# Usage: ./right.sh "design the authentication system"
exec "$(dirname "$0")/trigger.sh" right "$@"
