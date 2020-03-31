#!/bin/bash -e

# Debugging
set -x

# Environment
export SHELL=/bin/bash

# Install cp2k code.
verdi code show cp2k@localhost || verdi code setup --config /opt/aiida-cp2k/.docker/cp2k-code.yml --non-interactive
