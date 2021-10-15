[![Latest release](https://img.shields.io/github/v/release/biosimulators/Biosimulators_test_suite)](https://github.com/biosimulators/Biosimulators_test_suite/releases)
[![PyPI](https://img.shields.io/pypi/v/Biosimulators-test-suite)](https://pypi.org/project/Biosimulators-test-suite/)
[![CI status](https://github.com/biosimulators/Biosimulators_test_suite/workflows/Continuous%20integration/badge.svg)](https://github.com/biosimulators/Biosimulators_test_suite/actions?query=workflow%3A%22Continuous+integration%22)
[![Test coverage](https://codecov.io/gh/biosimulators/Biosimulators_test_suite/branch/dev/graph/badge.svg)](https://codecov.io/gh/biosimulators/Biosimulators_test_suite)
[![All Contributors](https://img.shields.io/github/all-contributors/biosimulators/Biosimulators_test_suite/HEAD)](#contributors-)

# BioSimulators test suite

The BioSimulators test suite is a tool for validating that biosimulation software tools implement the [BioSimulators conventions for biosimulation tools](https://biosimulators.org/conventions).

The test suite is composed of two parts:

* [A collection of example modeling projects](examples). Each project is represented by a single [COMBINE/OMEX archive](https://combinearchive.org/) that contains one or more simulation experiments described using the [Simulation Experiment Description Markup Language (SED-ML)](https://sed-ml.org) and one or more models described using a format such as the [BioNetGen Language (BNGL)](https://bionetgen.org) or the [Systems Biology Markup Language (SBML)](http://sbml.org).

* Software for checking that biosimulation tools execute these projects according to the BioSimulators conventions.

    * Simulation tools support the [BioSimulators standard command-line arguments](https://biosimulators.org/conventions/simulator-interfaces).
    * Simulation tools support the [BioSimulators conventions for Docker images](https://biosimulators.org/conventions/simulator-images).
    * Simulation tools follow the [BioSimulators conventions for executing simulations described by SED-ML files in COMBINE/OMEX archives](https://biosimulators.org/conventions/simulation-experiments).
    * Simulation tools support the [BioSimulators conventions for the outputs of SED-ML files in COMBINE/OMEX archives](https://biosimulators.org/conventions/simulation-reports).

## Installation instructions, tutorial, and API documentation
Installation instructions, tutorial, and API documentation are available [here](https://docs.biosimulators.org/Biosimulators_test_suite/).

## License
The software in this package is released under the [MIT License](LICENSE). The modeling projects in this package are released under the [Creative Commons 1.0 Universal (CC0) license](LICENSE-DATA).

## Development team
This package was developed by the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York, the [https://health.uconn.edu/cell-analysis-modeling/](https://health.uconn.edu/cell-analysis-modeling/) at the University of Connecticut, and the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) with assistance from the contributors listed [here](CONTRIBUTORS.md).

## Contributing to the test suite
We enthusiastically welcome contributions to the test suite! Please see the [guide to contributing](CONTRIBUTING.md) and the [developer's code of conduct](CODE_OF_CONDUCT.md).

## Acknowledgements
This work was supported by National Institutes of Health award P41EB023912.

## Questions and comments
Please contact the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments.
