# Example COMBINE/OMEX archives

This directory is a collection of example [COMBINE/OMEX archives](https://combinearchive.org/) that describe
simulations of biological models. As detailed below, the archives in this directory involve a variety of modeling frameworks
(e.g., logical, constraint-based), simulation algorithms (e.g., CVODE, SSA), and model formats (e.g., BNGL, SBML). All
of the simulations in the archives in this directory are described using the
[Simulation Experiment Description Markup Language (SED-ML)](https://sed-ml.org).

The purpose of this directory is two-fold:

* This directory serves as a reference for the community.
* The directory serves as a test suite for the [BioSimulators](https://biosimulators.org) registry of biosimulation tools.
  Tools submitted to the registry are validated using the software in this repository and the examples in this directory.

## Contents
* [Modeling frameworks employed by the archives](#modeling-frameworks-employed-by-the-example-archives)
* [Simulation algorithms employed by the archives](#simulation-algorithms-employed-by-the-example-archives)
* [Model formats employed by the archives](#model-formats-employed-by-the-example-archives)
* [Compatibility of the archives with simulation tools](#compatibility-of-the-example-archives-with-simulation-tools)

## Modeling frameworks employed by the example archives

The archives in this directory involve the following modeling frameworks:

| Name                   | Status      | SBO id                                                                                                           |
| ---------------------- | ------------| ---------------------------------------------------------------------------------------------------------------- |
| flux balance           | coming soon | [SBO_0000624](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000624) |
| logical                | coming soon | [SBO_0000234](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000234) |
| non-spatial continuous |             | [SBO_0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293) |
| non-spatial discrete   |             | [SBO_0000295](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000295) |

## Simulation algorithms employed by the example archives

The archives in this directory involve numerous simulation algorithms such as:

| Name                            | Acronym | KiSAO id                                                                                                                             |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Code Value Ordinary Differential Equation Solver | CVODE | [KISAO_0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019) |
| Stochastic Simulation Algorithm | SSA     | [KISAO_0000029](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000029) |

## Model formats employed by the example archives

The archives in this directory involve the following model formats:

| Name                                               | Acronym | EDAM id                                                                                                        |
| -------------------------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------- |
| [BioNetGen Language](https://bionetgen.org)        | BNGL    | [format_3972](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_3972) |
| [Systems Biology Markup Language](http://sbml.org) | SBML    | [format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585) |

## Compatibility of the example archives with simulation tools

Because each simulation tool only supports a limited number of modeling frameworks, simulation algorithms, and model formats, no simulation tool is capable of executing all of the archives in this directory. The [BioSimulators registry of biosimulation tools](https://biosimulators.org) contains detailed information about the modeling frameworks, simulation algorithms, and model formats supported by each registered tool. This information can be used to determine which tools are capable of executing a given archive.

Below is information about the compatibility of a selection of archives.

| Archive                  | Modeling framework (SBO id)      | Simulation algorithm (KiSAO id)  | Model format (EDAM id) | Compatibile simulators |
| ------------------------ | -------------------------------- | -------------------------------- | ---------------------- | ---------------------- |
| [`Caravagna-J-Theor-Biol....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | CVODE ([0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [tellurium](https://biosimulators.org/simulators/tellurium), [VCell](https://biosimulators.org/simulators/vcell)                 |
| [`Ciliberto-J-Cell-Biol....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex) | non-spatial discrete ([0000295](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000295)) | SSA ([0000029](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000029))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [GillesPy2](https://biosimulators.org/simulators/gillespy2), [tellurium](https://biosimulators.org/simulators/tellurium)                 |
| [`Parmar-BMC-Syst-Biol....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Parmar-BMC-Syst-Biol-2017-iron-distribution.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | CVODE ([0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [tellurium](https://biosimulators.org/simulators/tellurium), [VCell](https://biosimulators.org/simulators/vcell)                 |
| [`Szymanska-J-Theor-Biol....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Szymanska-J-Theor-Biol-2009-HSP-synthesis.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | CVODES ([0000496](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000496))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [AMICI](https://biosimulators.org/simulators/amici)     
| [`test-bngl.omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/bngl/test-bngl.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | CVODE ([0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019))           | BNGL ([format_3972](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_3972))     | [BioNetGen](https://biosimulators.org/simulators/bionetgen)  |
| [`Tomida-EMBO-J....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Tomida-EMBO-J-2003-NFAT-translocation.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | LSODA/LSODAR ([0000560](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000560))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [COPASI](https://biosimulators.org/simulators/copasi)                  |
| [`Varusai-Sci-Rep....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)) | LSODA/LSODAR ([0000560](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000560))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [COPASI](https://biosimulators.org/simulators/copasi)                  |
| [`Vilar-PNAS....omex`](https://github.com/biosimulators/Biosimulators_test_suite/raw/dev/examples/sbml-core/Vilar-PNAS-2002-minimal-circardian-clock.omex) | non-spatial continuous ([0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293)), non-spatial discrete ([0000295](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000295)) | CVODE ([0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019)), Forward Euler ([0000030](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000030)), NRM ([0000027](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000027))           | SBML ([format_2585](https://www.ebi.ac.uk/ols/ontologies/edam/terms?iri=http%3A%2F%2Fedamontology.org%2Fformat_2585))     | [VCell](https://biosimulators.org/simulators/vcell)                 |
