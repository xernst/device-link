#!/usr/bin/env bash
# Shortcut: send a task to the left brain.
# Usage: ./left.sh "run all tests and report failures"
exec "$(dirname "$0")/trigger.sh" left "$@"
