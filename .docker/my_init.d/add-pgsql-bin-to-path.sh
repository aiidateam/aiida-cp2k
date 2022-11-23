#!/bin/bash
set -em

# The following works in non-interactive mode
sed  -i '1i export PATH=${PATH}:/opt/conda/envs/pgsql/bin/' /home/aiida/.bashrc

# The following works in interactive mode
echo 'export PATH=${PATH}:/opt/conda/envs/pgsql/bin/' >> /home/aiida/.bashrc
