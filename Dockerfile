###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

FROM ubuntu:rolling
USER root

# silence tzdata's setup dialog
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

RUN apt-get update && apt-get install -yq --no-install-recommends \
    build-essential       \
    python-setuptools     \
    python-wheel          \
    python-pip            \
    python-dev            \
    postgresql            \
    less                  \
    nano                  \
    sudo                  \
    ssh                   \
    cp2k                  \
  && rm -rf /var/lib/apt/lists/*

# install python dependencies early to leverage docker build cache
RUN pip install flake8 aiida ase

# install aiida-cp2k
COPY . /opt/aiida-cp2k
WORKDIR /opt/aiida-cp2k/
RUN pip install .

# create ubuntu user with sudo powers
RUN adduser --disabled-password --gecos "" ubuntu               && \
    echo "ubuntu ALL=(ALL) NOPASSWD: ALL" >>  /etc/sudoers

# configure aiida
USER ubuntu
WORKDIR /opt/aiida-cp2k/test/
RUN ./configure_aiida.sh

CMD ./run_tests.sh

#EOF