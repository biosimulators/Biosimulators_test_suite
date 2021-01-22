# Contributing to the BioSimulators test suite

We enthusiastically welcome contributions to the BioSimulators test suite!

## Coordinating contributions

Before getting started, please contact the lead developers at [info@biosimulators.org](mailto:info@biosimulators.org) to coordinate your planned contributions with other ongoing efforts. Please also use GitHub issues to announce your plans to the community so that other developers can provide input into your plans and coordinate their own work. As the development community grows, we will institute additional infrastructure as needed such as a leadership committee and regular online meetings.

## Repository organization

This repository follows standard Python conventions:

* `README.md`: Overview of this repository
* `biosimulators_test_suite/`: Source code for this package
* `examples`: Example modeling projects that the source code uses to test biosimulation software tools
* `examples-outputs`: Example outputs (reports and plots) of executing the example modeling projects
* `tests/`: Unit tests for the code for this package
* `setup.py`: pip installation script for this package
* `setup.cfg`: Configuration for the pip installation script
* `requirements.txt`: Dependencies of this package
* `requirements.optional.txt`: Optional dependencies of this package
* `MANIFEST.in`: List of files to include when the BioSimulators test suite is packaged for distribution through PyPI
* `LICENSE`: License for the sofware of this package
* `LICENSE-DATA`: License for the example modeling projects in this package
* `CONTRIBUTING.md`: Guide to contributing to this package (this document)
* `CODE_OF_CONDUCT.md`: Code of conduct for developers of this package

## Coding convention

The code in this repository follows standard Python style conventions:

* Class names: `UpperCamelCase`
* Function names: `lower_snake_case`
* Variable names: `lower_snake_case`

## Documentation convention

The code in the BioSimulators test suite is documented using [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) and the [napoleon Sphinx plugin](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html). The documentation can be compiled with [Sphinx](https://www.sphinx-doc.org/) by running the following commands:

```
python -m pip install -r docs-src/requirements.txt
sphinx-apidoc . setup.py --output-dir docs-src/source --force --module-first --no-toc
sphinx-build docs-src docs
```

## Submitting changes

Please use GitHub pull requests to submit changes. Each request should include a brief description of the new and/or modified features.

## Releasing new versions

To release changes, contact the [lead developers](mailto:info@biosimulators.org) to request their release.

Below are instructions for releasing a new version:

1. Commit the changes to this repository.
2. Increment the `__version__` variable in `biosimulators_test_suite/_version.py`.
3. Commit this change to `biosimulators_test_suite/_version.py`.
4. Merge the changes in to the `deploy` branch:
    ```
    git checkout deploy
    git merge dev
    ```
5. Add a tag for the new version by running `git tag { version }`. `version` should be equal to the value of the
   `__version__` variable in `biosimulators_test_suite/_version.py`.
6. Push these commits and the new tag to GitHub by running `git push && git push --tags`.
7. This push will trigger a GitHub action which will execute the following tasks:
   * Create a GitHub release for the version.
   * Push the release to PyPI.
   * Compile the documentation and push the compiled documentation to the repository so that the new documentation is viewable at github.io.

## Reporting issues

Please use [GitHub issues](https://github.com/biosimulators/Biosimulators_test_suite/issues) to report any issues to the development community.

## Getting help

Please use [GitHub issues](https://github.com/biosimulators/Biosimulators_test_suite/issues) to post questions or contact the lead developers at [info@biosimulators.org](mailto:info@biosimulators.org).
