#!/bin/bash
set -em

su -c /opt/add-codes.sh aiida

# Make /opt/aiida-cp2k folder editable for the $SYSTEM_USER.
chown -R aiida:aiida /opt/aiida-cp2k/
