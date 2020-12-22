Installation instructions
=========================

Install the dependencies for the test suite
-------------------------------------------

First, install the following dependencies of the test suite:

* `Docker <https://www.docker.com/>`_
* `Python <https://www.python.org/downloads/>`_ (>= 3.7)
* `pip <https://pip.pypa.io/>`_

Install the optional dependencies for the test suite
----------------------------------------------------

To check that Docker image for simulation tools can be converted into Singularity images, also install Singularity. Installation instructions are available at `https://sylabs.io/docs/ <https://sylabs.io/docs/>`_.


Install the test suite
----------------------

After installing the dependencies outlined above, run the command below to install the BioSimulators test suite. Although the test suite is available from PyPI, we recommend installing the test suite from the Git repository because the package in PyPI does not include the example COMBINE archives needed for most of the tests.

.. code-block:: text

    git clone --branch deploy https://github.com/biosimulators/Biosimulators_test_suite.git
    pip install -e Biosimulators_test_suite
