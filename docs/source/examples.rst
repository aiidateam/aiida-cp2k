Examples
--------

See `examples` folder for complete examples of setting up a calculation or a work chain.


Simple calculation
==================

.. code-block:: bash

    cd examples/single_calculations
    verdi run example_dft.py <code_label>         # Submit example calculation.
    verdi process list -a -p1                     # Check status of calculation.


Work chain
==========

.. code-block:: bash

    cd examples/workchains
    verdi run example_base.py <code_label>       # Submit test calculation.
    verdi process list -a -p1                     # Check status of the work chain.