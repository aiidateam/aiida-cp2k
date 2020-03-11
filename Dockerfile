###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

FROM aiidateam/aiida-docker-stack

# Set HOME variable:
ENV HOME="/home/aiida"
ENV PATH="${HOME}/.local/bin:${PATH}"


# Install CP2K.
RUN apt-get update && apt-get install -y --no-install-recommends cp2k

# Install aiida-cp2k.
COPY . ${HOME}/code/aiida-cp2k
RUN chown -R aiida:aiida ${HOME}/code

# Now do everything as the aiida user.
USER aiida

# Set the plugin folder as the workdir.
WORKDIR ${HOME}/code/aiida-cp2k

# Install aiida-cp2k plugin and coveralls
RUN pip install --user .[pre-commit,test]
RUN pip install --user coveralls

# Populate reentry cache for aiida user https://pypi.python.org/pypi/reentry/.
RUN reentry scan

# Install the cp2k code.
COPY .docker/opt/add-codes.sh /opt/
COPY .docker/my_init.d/add-codes.sh /etc/my_init.d/40_add-codes.sh

# Change workdir back to $HOME.
WORKDIR ${HOME}

# Important to end as user root!
USER root

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]
