[![Build Status](https://travis-ci.org/aiidateam/aiida-cp2k.svg?branch=develop)](https://travis-ci.org/aiidateam/aiida-cp2k)
[![Coverage Status](https://coveralls.io/repos/github/aiidateam/aiida-cp2k/badge.svg?branch=develop)](https://coveralls.io/github/aiidateam/aiida-cp2k?branch=develop)
[![PyPI version](https://badge.fury.io/py/aiida-cp2k.svg)](https://badge.fury.io/py/aiida-cp2k)

# AiiDA CP2K
[AiiDA](http://www.aiida.net/) plugin for [CP2K](https://www.cp2k.org/).

## Documentation
The full documenation for this package can be found on [Read the Docs](https://aiida-cp2k.readthedocs.io/en/latest/)

## Installation

If you use `pip`, you can install it as: 
```
pip install aiida-cp2k
```

If you want to install the plugin in an editable mode, run:
```
git clone https://github.com/aiidateam/aiida-cp2k
cd aiida-cp2k
pip install -e .  # Also installs aiida, if missing (but not postgres/rabbitmq).
```

## Examples
See `examples` folder for complete examples of setting up a calculation or a work chain.

### Simple calculation
```shell
cd examples/single_calculations
verdi run example_dft.py <code_label>         # Submit example calculation.
verdi process list -a -p1                     # Check status of calculation.
```

### Work chain
```shell
cd examples/workchains
verdi run example_base.py  <code_label>       # Submit test calculation.
verdi process list -a -p1                     # Check status of the work chain.
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