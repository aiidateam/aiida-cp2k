#!/bin/bash
set -em

sed  -i '1i PATH=${PATH}:/opt/conda/envs/pgsql/bin/' /home/aiida/.bashrc
