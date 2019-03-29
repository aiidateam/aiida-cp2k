#!/bin/bash -e
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

set -x

#update reentry cache
reentry scan

#TODO: remove workaround
#      reentry stores files at ~/.config/reentry/data/<python-bin-path>
#      see also: https://github.com/DropD/reentry/issues/25
ln -s usr.bin.python ~/.config/reentry/data/usr.bin.python2

# configure postgreSQL
sudo service postgresql start
sudo -u postgres psql -d template1 -c "CREATE USER aiida WITH PASSWORD 'aiida_db_passwd';"
sudo -u postgres psql -d template1 -c "CREATE DATABASE aiidadb OWNER aiida;"
sudo -u postgres psql -d template1 -c "GRANT ALL PRIVILEGES ON DATABASE aiidadb to aiida;"

# setup aiida user
verdi setup                                       \
      --non-interactive                           \
      --email aiida@localhost                     \
      --first-name Some                           \
      --last-name Body                            \
      --institution XYZ                           \
      --backend django                            \
      --db-username aiida                         \
      --db-password aiida_db_passwd               \
      --db-name aiidadb                           \
      --db-host localhost                         \
      --db-port 5432                              \
      --repository /home/ubuntu/aiida_repository  \
      default

#bash -c 'echo -e "y\nsome.body@xyz.com" | verdi daemon configureuser'
verdi profile setdefault default

# setup local computer
mkdir -p /home/ubuntu/aiida_run

verdi computer setup               \
--non-interactive                  \
-L localhost                       \
-H localhost                       \
-T local                           \
-S direct                          \
--work-dir /home/ubuntu/aiida_run

verdi computer configure local localhost -n
verdi computer test localhost

# setup code
verdi code setup                \
--non-interactive               \
-L cp2k                         \
-Y localhost                    \
--remote-abs-path /usr/bin/cp2k \
--input-plugin cp2k             \

echo 'eval "$(verdi completioncommand)"' >> ~/.bashrc

# stop postgreSQL properly
sudo service postgresql stop

#EOF
