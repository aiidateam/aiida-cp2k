CP2K
------

Description
^^^^^^^^^^^
`CP2K`_ CP2K is a quantum chemistry and solid state physics software package that can perform atomistic simulations of solid state, liquid, molecular, periodic, material, crystal, and biological systems. CP2K provides a general framework for different modeling methods such as DFT using the mixed Gaussian and plane waves approaches GPW and GAPW. Supported theory levels include DFTB, LDA, GGA, MP2, RPA, semi-empirical methods (AM1, PM3, PM6, RM1, MNDO, …), and classical force fields (AMBER, CHARMM, …). CP2K can do simulations of molecular dynamics, metadynamics, Quantum Monte Carlo, Ehrenfest dynamics, vibrational analysis, core level spectroscopy, energy minimization, and transition state optimization using NEB or dimer method.

.. _CP2K: http://www.cp2k.org

Inputs
^^^^^^
* **kpoints**, class :py:class:`KpointsData <aiida.orm.data.array.kpoints.KpointsData>` (disabled)
  Reciprocal space points on which to build the wavefunctions. Currently not used,
  since experimental in CP2K.

* **parameters**, class :py:class:`ParameterData <aiida.orm.data.parameter.ParameterData>`
  Input parameters of CP2K, as a nested dictionary, mapping the input of CP2K.
  Example (CP2K input)::

      &GLOBAL
        RUN_TYPE ENERGY
        PRINT_LEVEL MEDIUM
        &TIMINGS
          THRESHOLD 0.001
        &END
      &END GLOBAL
      &FORCE_EVAL
        METHOD QS
        &DFT
          &MGRID
            NGRIDS 4
            CUTOFF 280
            REL_CUTOFF 30
          &END MGRID
          &QS
            EPS_DEFAULT 1.0E-12
            WF_INTERPOLATION PS
            EXTRAPOLATION_ORDER 3
          &END QS
          &SCF
            SCF_GUESS ATOMIC
            &OT ON
              MINIMIZER DIIS
            &END OT
            MAX_SCF 20
            EPS_SCF 1.0E-7
            &OUTER_SCF
              MAX_SCF 10
              EPS_SCF 1.0E-7
            &END OUTER_SCF
            &PRINT
              &RESTART OFF
              &END
            &END
          &END SCF
          &XC
            &XC_FUNCTIONAL Pade
            &END XC_FUNCTIONAL
          &END XC
        &END DFT
      &END FORCE_EVAL

  becomes (AiiDA input)::

      {'global': {
             'print_level': 'medium',
             'run_type': 'energy',
             'timings': {
                 'threshold': 0.001,
              },
         },
         'force_eval': {
             'method': 'quickstep',
             'dft': {
                 'qs': {
                     'eps_default': 1.0e-12,
                     'wf_interpolation': 'ps',
                     'extrapolation_order': 3,
                 },
                 'mgrid': {
                     'ngrids': 4,
                     'cutoff':280,
                     'rel_cutoff': 30,
                 },
                 'xc': {
                     'xc_functional': {
                         '_': 'PADE',
                     },
                 },
                 'scf': {
                     'SCF_GUESS': 'ATOMIC',
                     'OT': {
                         '_': 'ON',
                         'MINIMIZER': 'DIIS',
                     },
                     'MAX_SCF': 20,
                     'EPS_SCF': 1.0E-07,
                     'OUTER_SCF': {
                         'MAX_SCF': 10,
                         'EPS_SCF': 1.0E-7,
                     },
                     'PRINT': {
                         'RESTART': {
                             '_': 'OFF',
                         },
                     },
                 },
             },
        },
      }

* **structure**, class :py:class:`StructureData <aiida.orm.data.structure.StructureData>`

Outputs
^^^^^^^
There are several output nodes that can be created by the plugin, according to the calculation details.
All output nodes can be accessed with the ``calculation.out`` method.

* output_parameters :py:class:`ParameterData <aiida.orm.data.parameter.ParameterData>`
  (accessed by ``calculation.res``)
  Contains the scalar properties. Example: energy (in au),
  total_force (modulus of the sum of forces in ??au/Angstrom??).
* output_array :py:class:`ArrayData <aiida.orm.data.array.ArrayData>`
  Produced in case of calculations which do not change the structure, otherwise,
  an ``output_trajectory`` is produced.
  Contains vectorial properties, too big to be put in the dictionary.
  Example: forces (eV/Angstrom), stresses, ionic positions.
  Quantities are parsed at every step of the relaxation / molecular-dynamics run.
* output_trajectory :py:class:`ArrayData <aiida.orm.data.array.ArrayData>`
  Produced in case of calculations which change the structure, otherwise an
  ``output_array`` is produced. Contains vectorial properties, too big to be put
  in the dictionary. Example: forces (??au/Angstrom??), stresses, positions.
  Quantities are parsed at every step of the relaxation / molecular-dynamics run.
* output_structure :py:class:`StructureData <aiida.orm.data.structure.StructureData>`
  Present only if the calculation is moving the atoms.
  Cell and atomic positions refer to the last configuration.
* output_kpoints :py:class:`KpointsData <aiida.orm.data.array.kpoints.KpointsData>` (disabled)
  Present only if the calculation changes the cell shape.
  Kpoints refer to the last structure.

Errors
^^^^^^
Errors of the parsing are reported in the log of the calculation (accessible
with the ``verdi calculation logshow`` command).
Moreover, they are stored in the ParameterData under the key ``warnings``, and are
accessible with ``Calculation.res.warnings``.
