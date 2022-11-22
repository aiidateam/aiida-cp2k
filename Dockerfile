###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

FROM aiidateam/aiida-core:1.6.5

# To prevent the container to exit prematurely.
ENV KILL_ALL_RPOCESSES_TIMEOUT=50

WORKDIR /opt/

# Install statically linked CP2K which is a considerably newer release than Debian builtin.
# The statically linked CP2K is a non-MPI binary, but we're running all tests with 1 MPI proc.
RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends openmpi-bin ; \
  wget --no-verbose -O /usr/bin/cp2k https://github.com/cp2k/cp2k/releases/download/v8.2.0/cp2k-8.2-Linux-x86_64.ssmp ; \
  echo "1e6fccf901873ebe9c827f45fb29331f599772f6e6281e988d8956c7a3aa143c /usr/bin/cp2k" | sha256sum -c ; \
  chmod +x /usr/bin/cp2k

# Install aiida-cp2k plugin.
COPY . aiida-cp2k
RUN pip install ./aiida-cp2k[dev,docs]

# Install coverals.
RUN pip install coveralls

# Install the cp2k code.
COPY .docker/opt/add-codes.sh /opt/
COPY .docker/my_init.d/add-codes.sh /etc/my_init.d/50_add-codes.sh
