# -*- coding: utf-8 -*-

__version__ = "0.1.0"
from setuptools import setup

from os import path
from codecs import open

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='aiida-cp2k',
    version=__version__,
    description='CP2K plugin for AiiDA',
    long_description=long_description,
    url='https://bitbucket.org/yakutovich/aiida-cp2k',
    author='',
    author_email='',
    license='MIT',
    keywords='aiida cp2k plugin',
    install_requires=[
        'numpy',
        'aiida>=0.7.0'
    ],
    packages=["aiida_cp2k"],
    entry_points={
        'aiida.calculations': [
        "cp2k=aiida_cp2k.input"],
        'aiida.parsers': [
        "cp2k=aiida_cp2k.output_plugin"],
    },
)
