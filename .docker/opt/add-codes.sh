#!/bin/bash -e

# Debugging
set -x

# Environment
export SHELL=/bin/bash

# Install the ddec and cp2k codes
CP2K_FOLDER=/home/aiida/code/aiida-cp2k

verdi code show cp2k@localhost || verdi code setup --config ${CP2K_FOLDER}/.docker/cp2k-code.yml --non-interactive
