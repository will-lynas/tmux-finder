#!/usr/bin/env bash

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

tmux bind-key v display-popup -w '95%' -h '80%' -E "$CURRENT_DIR/tmux-finder.py"
