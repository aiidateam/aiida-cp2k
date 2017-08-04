#!/bin/bash -e

set -x

# install CP2K manually, unfortunatelly it was not packaged for Ubuntu 12.04
wget https://downloads.sourceforge.net/project/cp2k/precompiled/cp2k-4.1-Linux-x86_64.sopt
chmod +x cp2k-4.1-Linux-x86_64.sopt
CP2K_DATA_DIR=/home/krack/rt/released/cp2k/data
wget -O BASIS_MOLOPT https://sourceforge.net/p/cp2k/code/HEAD/tree/branches/cp2k-4_1-branch/cp2k/data/BASIS_MOLOPT?format=raw
wget -O POTENTIAL https://sourceforge.net/p/cp2k/code/HEAD/tree/branches/cp2k-4_1-branch/cp2k/data/POTENTIAL?format=raw
sudo mkdir -p ${CP2K_DATA_DIR}
sudo mv BASIS_MOLOPT POTENTIAL ${CP2K_DATA_DIR}

# install AiiDA
sudo pip install aiida

# ready the cp2k plugin
sudo pip install ase
sudo ln -s ${PWD}/aiida_cp2k/calculations /usr/local/lib/python2.7/dist-packages/aiida/orm/calculation/job/cp2k
sudo ln -s ${PWD}/aiida_cp2k/parsers      /usr/local/lib/python2.7/dist-packages/aiida/parsers/plugins/cp2k

# setup aiida user
verdi quicksetup --email some.body@xyz.com --first-name Some --last-name Body --institution XYZ
echo -e "y\nsome.body@xyz.com" | verdi daemon configureuser

# increase logging level
verdi devel setproperty logging.celery_loglevel DEBUG
verdi devel setproperty logging.aiida_loglevel DEBUG

# start the daemon
verdi daemon start

# setup local computer
cat > setup_computer.txt << EndOfMessage
localhost
localhost
The local computer
True
local
direct
$PWD/aiida_run

1
EndOfMessage

mkdir -p aiida_run
cat setup_computer.txt | verdi computer setup
verdi computer configure localhost
verdi computer test localhost

# setup code
cat > setup_code.txt << EndOfMessage
cp2k
CP2K from Ubuntu
False
cp2k
localhost
$PWD/cp2k-4.1-Linux-x86_64.sopt
EndOfMessage

cat setup_code.txt | verdi code setup

#EOF