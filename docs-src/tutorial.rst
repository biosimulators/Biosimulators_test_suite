Tutorial
==================================

Simulation software developers can utilize the test suite in two ways. First, developers can install and execute the test suite locally on their own machines. Second, developers can use the public cloud deployment of the test suite. In most cases, we recommend that developers use the public cloud deployment, which is easy to use. We recommend that developers deploy the test suite locally if they wish to test their simulator offline or wish to continuously test their simulator such as within their own continuous integration workflows (e.g., CircleCI, GitHub Actions).

Using the public cloud deployment of the test suite
---------------------------------------------------

The test suite is deployed as a GitHub Action workflow on issues submitted to the BioSimulators repository. Developers can run the test suite on their simulation tool by creating an issue with the label ``Validate/submit simulator``. Developers can create issues either using this `form <https://github.com/biosimulators/Biosimulators/issues/new?assignees=&labels=Validate%2Fsubmit+simulator&template=validate-submit-a-simulator.md&title=>`_ or using the GitHub API.

Once an issue is created, a GitHub Action workflow will use the test suite to validate and/or commit your simulator to the BioSimulators registry. If your simulator is valid, the workflow will post a success message to your issue. If the test suite finds that your simulator is invalid, the workflow will post a description of the error to your workflow.

Issue content and format
++++++++++++++++++++++++

The body of the issue should contain a YAML-encoded description of your simulator. This should describe the id of your simulator, the version of your simulator that you would like to validate or submit, a URL where the specifications of your simulator can be retrieved, and two flags which indicate whether you would like the Docker image for your simulator to be validated and whether you would like your simulator to be committed to the BioSimulators registry. Below is an example body for an issue.

.. code-block:: text

    ---
    id: tellurium
    version: 2.1.6
    specificationsUrl: https://raw.githubusercontent.com/biosimulators/Biosimulators_tellurium/2.1.6/biosimulators.json
    specificationsPatch:
      version: 2.1.6
      image:
        url: ghcr.io/biosimulators/Biosimulators_tellurium/tellurium:2.1.6
    validateImage: true
    commitSimulator: true
    ---

Validating and submitting simulators via the GitHub API
+++++++++++++++++++++++++++++++++++++++++++++++++++++++

Please follow these steps to use the GitHub API to programmatically submit issues to validate and/or submit simulators to the BioSimulators registry.

#. Create a GitHub account
#. Create a token for your GitHub account with the scope ``public_repo``
#. Execute HTTP POST requests to create issues. The body of the issue should be a JSON-encoded dictionary as illustrated below. The dictionary should have the following keys:

  * ``labels``: Its value should be equal to ``["Validate/submit simulator"]``.
  * ``title``: A descriptive title for your issue such as ``Submit tellurium 2.1.6``.
  * ``body``: A YAML-encoded description of your simulator as outlined above.

.. code-block:: text

    GH_USERNAME=*********
    GH_TOKEN=*********
    curl \
      -X POST \
      -u ${GH_USERNAME}:${GH_TOKEN} \
      -H "Accept: application/vnd.github.v3+json" \
      https://api.github.com/repos/biosimulators/Biosimulators/issues \
      -d '{"labels": ["Validate/submit simulator"], "title": "Submit tellurium 2.1.6", "body": "---\nname: tellurium\nversion: 2.1.6\nspecificationsUrl: https://raw.githubusercontent.com/biosimulators/Biosimulators_tellurium/2.1.6/biosimulators.json\nspecificationsPatch:\n  version: 2.1.6\n  image:\n    url: ghcr.io/biosimulators/biosimulators_tellurium/tellurium:2.1.6\nvalidateImage: true\ncommitSimulator: true\n\n---"}'


Running the test suite locally
---------------------------------------------------

The test suite can also be run locally as illustrated below.

.. code-block:: text

    # Run all tests
    biosimulators-test-suite /path/to/simulator/specifications.json

    # Run a specific test
    biosimulators-test-suite /path/to/simulator/specifications.json \
      --test-case \
        sedml.SimulatorSupportsModelAttributeChanges

    # Run multiple specific tests
    biosimulators-test-suite /path/to/simulator/specifications.json \
      --test-case \
        sedml.SimulatorSupportsModelAttributeChanges \
        published_project.SimulatorCanExecutePublishedProject:sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations \
        published_project.SimulatorCanExecutePublishedProject:sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint


Directly testing a command-line interface (rather than a Docker image)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Optionally, the ``--cli`` argument can be used to instruct the test suite to directly verify a command interface
rather than indirectly verify the interface through the entry point of a Docker image. Note, the Docker image tests will still
use the Docker image.

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --cli /usr/local/bin/tellurium


Executing the test suite with stdout/stderr capturing disabled
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Some Mac OS users have reported that capturer, the package that the test suite uses to collect the standard output and error produced by each test case, fails on their systems. In such cases, the ``--do-not-log-std-out-err`` option can be used to disable the collection of standard output and error.

.. code-block:: text

  biosimulators-test-suite /path/to/simulator/specifications.json \
    --do-not-log-std-out-err


Saving the synthetic COMBINE archives generated by the test cases
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Optionally, the ``--synthetic-archives-dir`` argument can be used to save the synthetic
COMBINE/OMEX archives generated by the test cases to a directory. This enables developers
to inspect how the test suite verifies simulation tools. 

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --synthetic-archives-dir /path/to/save/synthetic-archives

The synthetically-generated archives will be saved to a separate sub-sub-directory for each test
case in a separate sub-directory for each test module. The files will have names that indicate the
order in which they were executed and whether simulators are expected to sucessfully execute
the archive or not. For example, the archive generated by the 
:py:class:`biosimulators_test_suite.test_case.sedml.SimulatorSupportsMultipleTasksPerSedDocument`
test case will be saved to
``/path/to/save/synthetic-archives/sedml/SimulatorSupportsMultipleTasksPerSedDocument/1.execution-should-succeed.omex``.

Additionally, ``--dry-run`` argument can be used to export these synthetic COMBINE/OMEX archives
without using your simulator to execute them.

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --synthetic-archives-dir /path/to/save/synthetic-archives
      --dry-run


Saving the outputs of the execution of COMBINE archives involved in the test cases
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Optionally, the ``--work-dir`` argument can be used to save the COMBINE archives involved in the test cases and the 
outputs (reports and plots) generated by their execution to a directory. This enables developers
to inspect how the test suite verifies simulation tools. 

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --work-dir /path/to/save/archives-and-their-outputs

The files involved in each test case will be saved to a separate sub-sub-directory for each test
case in a separate sub-directory for each test module. The files will have names that indicate the
order in which they were executed. For example, the archive generated by the 
:py:class:`biosimulators_test_suite.test_case.sedml.SimulatorSupportsMultipleTasksPerSedDocument`
test case will be saved to
``/path/to/save/archives-and-their-outputs/sedml/SimulatorSupportsMultipleTasksPerSedDocument/``.


Display additional diagnostic information (tracebacks for test failures)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Optionally, the ``--debug`` argument can be used to display traceback information about the origin
of each failed test (Line of Python code where the error occurred and the stack of calls which led
to its execution).

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --debug


Saving the results of the test cases to a file
++++++++++++++++++++++++++++++++++++++++++++++

Optionally, the ``--report`` argument can be used to save the results of the test cases
to a JSON file.

.. code-block:: text

    biosimulators-test-suite /path/to/simulator/specifications.json \
      --report /path/to/save/results.json
