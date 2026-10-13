###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

# The services image release and the tested Python package version are separate.
ARG AIIDA_IMAGE_VERSION=2.5.2

FROM aiidateam/aiida-core-with-services:${AIIDA_IMAGE_VERSION}

ARG AIIDA_VERSION=2.9.2


# To prevent the container to exit prematurely.
ENV KILL_ALL_RPOCESSES_TIMEOUT=50

USER root
RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends libsymspg1

USER aiida

# Run the plugin and service setup with the supported Python interpreter.
# The older services image pins Python 3.10; override that pin for CI.
RUN sed -i '/^python /d' "${CONDA_DIR}/conda-meta/pinned" && \
    mamba install --yes -n base -c conda-forge "python=3.12" pip mamba && \
    mamba clean --all -f -y

RUN mamba create --yes -c conda-forge -n cp2k cp2k=9.1 && mamba clean --all -f -y

# Install aiida-cp2k plugin.
COPY --chown="${SYSTEM_UID}:${SYSTEM_GID}" . /home/aiida/aiida-cp2k

# Resolve the requested AiiDA version together with the plugin dependencies.
RUN pip install "aiida-core==${AIIDA_VERSION}" "./aiida-cp2k[dev,docs]"
RUN python -c "import sys; import importlib.metadata as m; print('Testing Python', sys.version); assert sys.version_info[:2] == (3, 12); print('Testing aiida-core', m.version('aiida-core')); assert m.version('aiida-core') == '${AIIDA_VERSION}'"

# Install coverals.
RUN pip install coveralls

# Install the cp2k code.
COPY .docker/init/add-codes.sh /etc/init/
COPY .docker/s6-rc.d/cp2k-code-setup /etc/s6-overlay/s6-rc.d/cp2k-code-setup
COPY .docker/user/cp2k-code-setup /etc/s6-overlay/s6-rc.d/user/contents.d/cp2k-code-setup
