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

    # Run specific tests
    biosimulators-test-suite /path/to/simulator/specifications.json \
      --combine-case \
        sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations
        sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint
