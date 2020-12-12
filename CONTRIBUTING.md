# Contributing to the BioSimulations COMBINE archive test suite

We enthusiastically welcome contributions to the BioSimulations COMBINE archive test suite!

## Coordinating contributions

Before getting started, please contact the lead developers at [info@biosimulators.org](mailto:info@biosimulators.org) to coordinate your planned contributions with other ongoing efforts. Please also use GitHub issues to announce your plans to the community so that other developers can provide input into your plans and coordinate their own work. As the development community grows, we will institute additional infrastructure as needed such as a leadership committee and regular online meetings.

## Repository organization

* `README.md`: Overview of the test suite
* `biosimulators_test_suite/`: collection of COMBINE/OMEX archives (`.omex` files) and metadata about each archive (one JSON file per archive)
* `LICENSE`: License
* `CONTRIBUTING.md`: Guide to contributing to the test suite (this document)
* `CODE_OF_CONDUCT.md`: Code of conduct for developers

## Submitting changes

Please use GitHub pull requests to submit changes. Each request should include a brief description of the new and/or modified features.

## Releasing new versions

To release changes, contact the [lead developers](mailto:info@biosimulators.org) to request their release.

Below are instructions for releasing a new version:

1. Commit the changes to this repository.
2. Increment the `__version__` variable in `biosimulators_test_suite/_version.py`.
3. Commit this change to `biosimulators_test_suite/_version.py`.
4. Add a tag for the new version by running `git tag { version }`. `version` should be equal to the value of the
   `__version__` variable in `biosimulators_test_suite/_version.py`.
5. Push these commits and the new tag to GitHub by running `git push && git push --tags`.
6. This push will trigger a GitHub action which will execute the following tasks:
   * Create a GitHub release for the version.
   * Push the release to PyPI.
   * Compile the documentation and push the compiled documentation to the repository so that the new documentation is viewable at github.io.

## Reporting issues

Please use [GitHub issues](https://github.com/biosimulators/Biosimulators_test_suite/issues) to report any issues to the development community.

## Getting help

Please use [GitHub issues](https://github.com/biosimulators/Biosimulators_test_suite/issues) to post questions or contact the lead developers at [info@biosimulators.org](mailto:info@biosimulators.org).
