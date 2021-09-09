BioSimulators test suite documentation
===========================================

The BioSimulators test suite is a tool for validating that biosimulation software tools implement the `BioSimulators conventions for biosimulation tools <https://biosimulators.org/conventions>`_.

The test suite is composed of two parts:

* A collection of example modeling projects. Each project is represented by a single `COMBINE/OMEX archive <https://combinearchive.org/>`_ that contains one or more simulation experiments described using the `Simulation Experiment Description Markup Language (SED-ML) <https://sed-ml.org>`_ and one or more models described using a format such as the `BioNetGen Language (BNGL) <https://bionetgen.org>`_) or the `Systems Biology Markup Language (SBML) <http://sbml.org>`_.

* Software for checking that biosimulation tools execute these projects according to the BioSimulators conventions.

    * Simulation tools support the `BioSimulators standard command-line arguments <https://biosimulators.org/conventions/simulator-interfaces>`_.
    * Simulation tools support the `BioSimulators conventions for Docker images <https://biosimulators.org/conventions/simulator-images>`_.
    * Simulation tools follow the `BioSimulators conventions for executing simulations described by SED-ML files in COMBINE/OMEX archives <https://biosimulators.org/conventions/simulation-experiments>`_.
    * Simulation tools support the `BioSimulators conventions for the outputs of SED-ML files in COMBINE/OMEX archives <https://biosimulators.org/conventions/simulation-reports>`_.

Contents
--------

.. toctree::
   :maxdepth: 2

   installation.rst
   tutorial.rst
   API documentation <source/biosimulators_test_suite.rst>
   about.rst
   genindex.rst
