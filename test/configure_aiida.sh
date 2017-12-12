#!/bin/bash -e

set -x

#update reentry cache
sudo reentry scan

# configure postgreSQL
sudo service postgresql start
sudo -u postgres psql -d template1 -c "CREATE USER aiida WITH PASSWORD 'aiida_db_passwd';"
sudo -u postgres psql -d template1 -c "CREATE DATABASE aiidadb OWNER aiida;"
sudo -u postgres psql -d template1 -c "GRANT ALL PRIVILEGES ON DATABASE aiidadb to aiida;"

# setup aiida user
verdi setup                                 \
      --non-interactive                     \
      --email aiida@localhost               \
      --first-name Some                     \
      --last-name Body                      \
      --institution XYZ                     \
      --backend django                      \
      --db_user aiida                       \
      --db_pass aiida_db_passwd             \
      --db_name aiidadb                     \
      --db_host localhost                   \
      --db_port 5432                        \
      --repo /home/ubuntu/aiida_repository  \
      default

#bash -c 'echo -e "y\nsome.body@xyz.com" | verdi daemon configureuser'
verdi profile setdefault verdi default
verdi profile setdefault daemon default

# increase logging level
verdi devel setproperty logging.celery_loglevel DEBUG
verdi devel setproperty logging.aiida_loglevel DEBUG

# setup local computer
cat > /tmp/setup_computer.txt << EndOfMessage
localhost
localhost
The local computer
True
local
direct
/home/ubuntu/aiida_run

1
EndOfMessage

mkdir -p /home/ubuntu/aiida_run
cat /tmp/setup_computer.txt | verdi computer setup
verdi computer configure localhost
verdi computer test localhost

# setup code
cat > /tmp/setup_code.txt << EndOfMessage
cp2k
CP2K from Ubuntu
False
cp2k
localhost
/usr/bin/cp2k
EndOfMessage

cat /tmp/setup_code.txt | verdi code setup

echo 'eval "$(verdi completioncommand)"' >> ~/.bashrc

# stop postgreSQL properly
sudo service postgresql stop

#EOF
