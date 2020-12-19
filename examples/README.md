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

## Modeling frameworks employed by the archives in this directory

The archives in this directory involve the following modeling frameworks:

| Name                   | Status      | SBO id                                                                                                           |
| ---------------------- | ------------| ---------------------------------------------------------------------------------------------------------------- |
| flux balance           | coming soon | [SBO_0000624](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000624) |
| logical                | coming soon | [SBO_0000234](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000234) |
| non-spatial continuous |             | [SBO_0000293](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000293) |
| non-spatial discrete   |             | [SBO_0000295](https://www.ebi.ac.uk/ols/ontologies/sbo/terms?iri=http%3A%2F%2Fbiomodels.net%2FSBO%2FSBO_0000295) |

## Simulation algorithms employed by the archives in this directory

The archives in this directory involve numerous simulation algorithm such as:

| Name                            | Acronym | KiSAO id                                                                                                                             |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| CVODE                           |         | [KISAO_0000019](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000019) |
| Stochastic Simulation Algorithm | SSA     | [KISAO_0000029](https://www.ebi.ac.uk/ols/ontologies/kisao/terms?iri=http%3A%2F%2Fwww.biomodels.net%2Fkisao%2FKISAO%23KISAO_0000029) |

## Model formats employed by the archives in this directory

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
| [Varusai-Sci-Rep-2018](Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML) | non-spatial continuous (0000293) | LSODA/LSODAR (0000560)           | SBML (format_2585)     | copasi                 |
