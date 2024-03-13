[![PyPI version](https://badge.fury.io/py/aiida-cp2k.svg)](https://badge.fury.io/py/aiida-cp2k)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aiida-cp2k.svg)](https://pypi.python.org/pypi/aiida-cp2k/)
[![Test CI](https://github.com/aiidateam/aiida-cp2k/actions/workflows/ci.yml/badge.svg)](https://github.com/aiidateam/aiida-cp2k/actions)
[![Coverage Status](https://coveralls.io/repos/github/aiidateam/aiida-cp2k/badge.svg?branch=main)](https://coveralls.io/github/aiidateam/aiida-cp2k?branch=main)
[![Documentation](https://readthedocs.org/projects/aiida-cp2k/badge/?version=latest)](https://aiida-cp2k.readthedocs.io/en/latest/?badge=latest)

# AiiDA CP2K

[AiiDA](http://www.aiida.net/) plugin for [CP2K](https://www.cp2k.org/).

## Installation

If you use `pip`, you can install it as:
```
pip install aiida-cp2k
```

To install the plugin in an editable mode, run:
```
git clone https://github.com/aiidateam/aiida-cp2k
cd aiida-cp2k
pip install -e .  # Also installs aiida, if missing (but not postgres/rabbitmq).
```

## Links

* [Documentation](https://aiida-cp2k.readthedocs.io/en/latest/) for the calculation examples and features of the plugin.
* [Make an issue](https://github.com/aiidateam/aiida-cp2k/issues/new) for bug reports, questions and suggestions.
* [AiiDA](http://www.aiida.net/) to learn about AiiDA.
* [CP2K](https://www.cp2k.org/) to learn about CP2K.

## For maintainers

### Release

To create a new release, clone the repository, install development dependencies with `pip install '.[dev]'`, and then execute `bumpver update --major/--minor/--patch`.
This will:

  1. Create a tagged release with bumped version and push it to the repository.
  2. Trigger a GitHub actions workflow that creates a GitHub release.

Additional notes:

  - Use the `--dry` option to preview the release change.
  - The release tag (e.g. a/b/rc) is determined from the last release.
    Use the `--tag` option to override the release tag.

### Testing

To run the tests, you need to have Docker installed in your system.
Once this is done, you can build the Docker image with the following command:

```bash
docker build -t aiida_cp2k_test .
```
Then, you can launch the container:

```bash
DOKERID=`docker run -d aiida_cp2k_test`
```
This will remeber the container ID in the variable `DOKERID`.
You can then run the tests with the following command:

```bash
docker exec --tty --user aiida $DOCKERID /bin/bash -l -c 'cd /home/aiida/aiida-cp2k/ && pytest'
```

To enter the container for manual testing do:

```bash
docker exec -it --user aiida $DOCKERID bash
```


## License

MIT

## Contact

yakutovicha@gmail.com


## Acknowledgements

This work is supported by:
* the [MARVEL National Centre for Competency in Research](http://nccr-marvel.ch) funded by the [Swiss National Science Foundation](http://www.snf.ch/en);
* the [MaX European Centre of Excellence](http://www.max-centre.eu/) funded by the Horizon 2020 EINFRA-5 program, Grant No. 676598;
* the [swissuniversities P-5 project "Materials Cloud"](https://www.materialscloud.org/swissuniversities).

<img src="miscellaneous/logos/MARVEL.png" alt="MARVEL" style="padding:10px;" width="150"/>
<img src="miscellaneous/logos/MaX.png" alt="MaX" style="padding:10px;" width="250"/>
<img src="miscellaneous/logos/swissuniversities.png" alt="swissuniversities" style="padding:10px;" width="250"/>
