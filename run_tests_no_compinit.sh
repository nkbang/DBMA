#!/bin/zsh
unsetopt autocd
autoload -Uz compinit && compaudit &>/dev/null || true
source /Users/David/envs/dbma311/bin/activate
python -m pytest test_dbma.py -v