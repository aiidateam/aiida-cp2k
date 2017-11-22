# AiiDA CP2K
This is the official CP2K plugin for AiiDA.

# Install

Simply install via setuptools:

	pip install .

The new plugin system will ensure that the entry points are automatically registered upon installation.

# Examples

The [test folder](./test) contains example scripts that demonstrate most features.

# Testing

Every commit and pull request is automatically tested by [TravisCI](https://travis-ci.org/cp2k/aiida-cp2k/).

To run the tests locally install [Docker](https://docs.docker.com/engine/installation/) and execute the following commands:
```
git clone https://github.com/cp2k/aiida-cp2k
docker build -t aiida_cp2k_test aiida-cp2k
docker run -it --init aiida_cp2k_test
```
