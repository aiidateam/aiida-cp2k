###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

ARG AIIDA_VERSION=2.9.3

FROM aiidateam/aiida-core-with-services:aiida-${AIIDA_VERSION}

# Re-declare to make the pre-FROM value available to RUN instructions.
ARG AIIDA_VERSION

# To prevent the container to exit prematurely.
ENV KILL_ALL_RPOCESSES_TIMEOUT=50

USER root
RUN set -ex ; \
  apt-get update ; \
  apt-get install -y --no-install-recommends libsymspg1

USER aiida

RUN mamba create --yes -c conda-forge -n cp2k cp2k=9.1 && mamba clean --all -f -y

# Install aiida-cp2k plugin.
COPY --chown="${SYSTEM_UID}:${SYSTEM_GID}" . /home/aiida/aiida-cp2k

# Pin aiida-core so the plugin install cannot replace the image's version.
# PyPI cp2k-input-tools 0.9.1 still requires Pint <0.24. Upstream PR #106
# permits Pint 0.24, which supports NumPy 2; use that exact fix in CI until released.
RUN pip install \
    "aiida-core==${AIIDA_VERSION}" \
    "cp2k-input-tools @ git+https://github.com/cp2k/cp2k-input-tools.git@027cc072012e373265ba8368973a4a7158e33a19" \
    "pint==0.24.4" \
    ./aiida-cp2k[dev,docs]

# Install coverals.
RUN pip install coveralls

# Install the cp2k code.
COPY .docker/init/add-codes.sh /etc/init/
COPY .docker/s6-rc.d/cp2k-code-setup /etc/s6-overlay/s6-rc.d/cp2k-code-setup
COPY .docker/user/cp2k-code-setup /etc/s6-overlay/s6-rc.d/user/contents.d/cp2k-code-setup
