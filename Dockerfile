###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################


FROM aiidateam/aiida-core-with-services:2.5.0


# To prevent the container to exit prematurely.
ENV KILL_ALL_RPOCESSES_TIMEOUT=50

RUN conda create --yes -c conda-forge -n cp2k cp2k=9.1 && conda clean --all -f -y

# Install aiida-cp2k plugin.
COPY --chown="${SYSTEM_UID}:${SYSTEM_GID}" . /home/aiida/aiida-cp2k
RUN pip install ./aiida-cp2k[dev,docs]

# Install coverals.
RUN pip install coveralls

# Install the cp2k code.
COPY .docker/init/add-codes.sh /etc/init/
COPY .docker/s6-rc.d/cp2k-code-setup /etc/s6-overlay/s6-rc.d/cp2k-code-setup
COPY .docker/user/cp2k-code-setup /etc/s6-overlay/s6-rc.d/user/contents.d/cp2k-code-setup
