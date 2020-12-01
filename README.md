[![License](https://img.shields.io/github/license/biosimulators/Biosimulators_test_suite.svg)](LICENSE)

# BioSimulators test suite

Collection of [COMBINE/OMEX](http://co.mbine.org/standards/omex) archives for testing [BioSimulators-compliant containerized simulation software tools](https://github.com/biosimulators/Biosimulators_simulator_template). The collection also serves as examples of COMBINE/OMEX archives.

[BioSimulations utils](https://github.com/biosimulations/biosimulations_utils) provides a utility for using the test suite to test containerized simulation tools. See below for more information.

## Contents
* [Usage: using the test suite to test a simulation tool](#usage-using-the-test-suite-to-test-a-biosimulators-compliant-containerized-simulation-tool)
* [License](#license)
* [Development team](#development-team)
* [Contributing to the test suite](#contributing-to-the-test-suite)
* [Acknowledgements](#acknowledgements)
* [Questions and comments](#questions-and-comments)

## Usage: using the test suite to test a BioSimulators-compliant containerized simulation tool
```python
from biosimulations_utils.simulator.testing import SimulatorValidator
dockerhub_id = 'biosimulators/tellurium'
properties_filename = '/path/to/Biosimulators_tellurium/biosimulators.json'
validator = SimulatorValidator()
valid_cases, failed_cases = validator.run(dockerhub_id, properties_filename)
```

## License
This package is released under the [Creative Commons CC0 license](LICENSE).

## Development team
This package was developed by the [Center for Reproducible Biomedical Modeling](http://reproduciblebiomodels.org) and the [Karr Lab](https://www.karrlab.org) at the Icahn School of Medicine at Mount Sinai in New York.

## Contributing to the test suite
We enthusiastically welcome contributions to the test suite! Please see the [guide to contributing](CONTRIBUTING.md) and the [developer's code of conduct](CODE_OF_CONDUCT.md).

## Acknowledgements
This work was supported by National Institutes of Health awards P41EB023912 and R35GM119771 and the Icahn Institute for Data Science and Genomic Technology.

## Questions and comments
Please contact the [BioSimulators Team](mailto:info@biosimulators.org) with any questions or comments.
