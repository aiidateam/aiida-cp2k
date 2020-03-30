Features
--------

Following the philosophy to ''enable without getting in the way'', this plugin provides access to all of CP2K's capabilities through a small set of well-tested features:

A full `CP2K input <https://manual.cp2k.org>`__ has to be provided as a nested Python dictionary `example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_dft.py>`__:

.. code-block:: python

    params = {'FORCE_EVAL': {'METHOD': 'Quickstep', 'DFT': { ... }}}
    builder.parameters = Dict(dict=params)


Section parameters are stored as key `_` in the dictionary:

.. code-block:: python

    xc_section = {'XC_FUNCTIONAL': {'_': 'LDA'}}

Repeated sections are stored as a list:

.. code-block:: python

    kind_section = [{'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-GTH', 'POTENTIAL': 'GTH-LDA'},
                {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-GTH', 'POTENTIAL': 'GTH-LDA'}]

Most data files (basis sets, pseudo potentials, VdW, etc.) are auto-discovered from CP2K's `data directory <https://github.com/cp2k/cp2k/tree/master/data>`__.

.. code-block:: python

    dft_section = {'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT', ...}


Additional data files can be added as AiiDA SinglefileData (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_mm.py>`__):

.. code-block:: python

    water_pot = SinglefileData(file=os.path.join("/tmp", "water.pot"))
    builder.file = {"water_pot": water_pot}

The start geometry can be provided as AiiDA StructureData (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_dft.py>`__):

.. code-block:: python

    structure = StructureData(ase=ase.io.read(os.path.join(thisdir, '..', "files", 'h2o.xyz')))

Alternatively the start geometry can be contained in the CP2K input (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_no_struct.py>`_):

.. code-block:: python

   'COORD': {' ': ['H    2.0   2.0   2.737166', 'H    2.0   2.0   2.000000']}

For restarting a calculation a parent folder can be attached  (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_restart.py>`__):

.. code-block:: python

   builder.parent_calc_folder = calc1['remote_folder']

By default only the output and restart file (if present) are retrieved. Additional files are retrieved upon request (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_mm.py>`__):

.. code-block:: python

   settings = Dict(dict={'additional_retrieve_list': ["runtime.callgraph"]})
   builder.settings = settings

The final geometry is extracted from the restart file (if present) and stored in AiiDA (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_geopt.py>`__):

.. code-block:: python

    dist = calc['output_structure'].get_ase().get_distance(0, 1)


The conversion of geometries between AiiDA and CP2K has a precision of at least 1e-10 Ångström (`example <https://github.com/aiidateam/aiida-cp2k/blob/develop/examples/single_calculations/example_precision.py>`__).