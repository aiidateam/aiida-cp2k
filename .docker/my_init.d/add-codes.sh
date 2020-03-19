#!/bin/bash
set -em

su -c /opt/add-codes.sh aiida

# Make /opt/aiida-cp2k folder editable for the $SYSTEM_USER.
chown -R ${SYSTEM_USER}:${SYSTEM_USER} /opt/aiida-cp2k/
