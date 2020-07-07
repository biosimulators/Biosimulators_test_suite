[![License](https://img.shields.io/github/license/KarrLab/Biosimulations_COMBINE_archive_test_suite.svg)](LICENSE)

# BioSimulations COMBINE archive test suite

Collection of [COMBINE/OMEX](http://co.mbine.org/standards/omex) archives for testing [BioSimulations-compliant containerized simulation software tools](https://github.com/reproducible-biomedical-modeling/Biosimulations_SimulatorDockerImageTemplate). The collection also serves as examples of COMBINE/OMEX archives.

[BioSimulations-utils](https://github.com/reproducible-biomedical-modeling/Biosimulations_utils) provides a utility for using the test suite to test containerized simulation tools. See below for more information.

## Contents
* [Usage: using the test suite to test a simulation tool](#usage-using-the-test-suite-to-test-a-biosimulations-compliant-containerized-simulation-tool)
* [License](#license)
* [Development team](#development-team)
* [Contributing to the test suite](#contributing-to-the-test-suite)
* [Acknowledgements](#acknowledgements)
* [Questions and comments](#questions-and-comments)

## Usage: using the test suite to test a BioSimulations-compliant containerized simulation tool
```python
from biosimulations_utils.simulator.testing import SimulatorValidator
dockerhub_id = 'crbm/biosimulations_tellurium'
properties_filename = '/path/to/Biosimulations_tellurium/properties.json'
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
Please contact the [Center for Reproducible Biomedical Modeling](mailto:info@reproduciblebiomodels.org) with any questions or comments.
