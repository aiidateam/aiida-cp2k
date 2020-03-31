#!/bin/bash -e

# Debugging
set -x

# Environment
export SHELL=/bin/bash

# Activate conda.
__conda_setup="$('/opt/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
        . "/opt/conda/etc/profile.d/conda.sh"
    else
        export PATH="/opt/conda/bin:$PATH"
    fi
fi
unset __conda_setup

# Install cp2k code.
verdi code show cp2k@localhost || verdi code setup --config /opt/aiida-cp2k/.docker/cp2k-code.yml --non-interactive
