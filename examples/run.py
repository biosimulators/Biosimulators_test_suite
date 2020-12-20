from biosimulators_utils.simulator import exec
import glob
import numpy
import os
import pandas
import shutil

BASE_DIR = os.path.dirname(__file__)
EXAMPLES = [
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex'),
        'simulators': ['tellurium'],
        'reports': [
            {
                'filename': 'BIOMD0000000912_sim.sedml/BIOMD0000000912_sim.csv',
                'number_of_points': 5001,
                'data_sets': 4,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Caravagna-J-Theor-Biol-2010-tumor-suppressive-oscillations.omex'),
        'simulators': ['vcell'],
        'reports': [
            {
                'filename': 'BIOMD0000000912_sim.sedml/Caravagna2010.csv',
                'number_of_points': 5001,
                'data_sets': 4,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex'),
        'simulators': ['tellurium'],
        'reports': [
            {
                'filename': 'simulation_1.sedml/simulation_1.csv',
                'number_of_points': 101,
                'data_sets': 20,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Ciliberto-J-Cell-Biol-2003-morphogenesis-checkpoint.omex'),
        'simulators': ['vcell'],
        'reports': [
            {
                'filename': 'simulation_1.sedml/simulation 1.csv',
                'number_of_points': 101,
                'data_sets': 22,  # VCell ignores reports
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Parmar-BMC-Syst-Biol-2017-iron-distribution.omex'),
        'simulators': ['tellurium'],
        'reports': [
            {
                'filename': 'Parmar2017_Deficient_Rich_tracer.sedml/simulation_1.csv',
                'number_of_points': 301,
                'data_sets': 2,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Parmar-BMC-Syst-Biol-2017-iron-distribution.omex'),
        'simulators': ['vcell'],
        'reports': [
            {
                'filename': 'Parmar2017_Deficient_Rich_tracer.sedml/simulation_1.csv',
                'number_of_points': 301,
                'data_sets': 23,  # VCell ignores reports
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Szymanska-J-Theor-Biol-2009-HSP-synthesis.omex'),
        'simulators': ['amici'],
        'reports': [
            {
                'filename': 'BIOMD0000000896_sim.sedml/BIOMD0000000896_sim.csv',
                'number_of_points': 4001,
                'data_sets': 10,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Tomida-EMBO-J-2003-NFAT-translocation.omex'),
        'simulators': ['copasi'],
        'reports': [
            {
                'filename': 'BIOMD0000000678_sim.sedml/BIOMD0000000678_sim.csv',
                'number_of_points': 801,
                'data_sets': 5,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Varusai-Sci-Rep-2018-mTOR-signaling-LSODA-LSODAR-SBML.omex'),
        'simulators': ['copasi'],
        'reports': [
            {
                'filename': 'LSODA.sedml/report_1_task1.csv',
                'number_of_points': 1001,
                'data_sets': 2,
            },
        ]
    },
    {
        'filename': os.path.join(BASE_DIR, 'sbml-core', 'Vilar-PNAS-2002-minimal-circardian-clock.omex'),
        'simulators': ['vcell'],
        'reports': [
            {
                'filename': 'simulation.sedml/tsk_0_0.csv',
                'number_of_points': 401,
                'data_sets': 2,
            },
            {
                'filename': 'simulation.sedml/tsk_0_1.csv',
                'number_of_points': 401,
                'data_sets': 2,
            },
            {
                'filename': 'simulation.sedml/tsk_0_2.csv',
                'number_of_points': 1001,
                'data_sets': 2,
            },
            {
                'filename': 'simulation.sedml/tsk_0_3.csv',
                'number_of_points': 1001,
                'data_sets': 2,
            },
            {
                'filename': 'simulation.sedml/tsk_1_0.csv',
                'number_of_points': 401,
                'data_sets': 2,
            },
            {
                'filename': 'simulation.sedml/tsk_1_1.csv',
                'number_of_points': 401,
                'data_sets': 2,
            },
        ]
    },    
]

BASE_OUTPUTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples-outputs'))


def run():
    if not os.path.isdir(BASE_OUTPUTS_DIR):
        os.makedirs(BASE_OUTPUTS_DIR)

    errors = []
    for example in EXAMPLES:
        for simulator in example['simulators']:
            example_out_dir = os.path.join(BASE_OUTPUTS_DIR, os.path.relpath(
                example['filename'].replace('.omex', '') + '-' + simulator, BASE_DIR))
            if os.path.isdir(example_out_dir):
                shutil.rmtree(example_out_dir)

            exec.exec_sedml_docs_in_archive_with_containerized_simulator(
                example['filename'],
                example_out_dir,
                'ghcr.io/biosimulators/{}:latest'.format(simulator),
            )

            reports = set([os.path.relpath(report.replace('.sedml', ''), example_out_dir)
                           for report in glob.glob(os.path.join(example_out_dir, '**/*.csv'), recursive=True)])
            expected_reports = set([report['filename'].replace('.sedml', '') for report in example['reports']])

            missing_reports = expected_reports.difference(reports)
            extra_reports = reports.difference(expected_reports)

            if missing_reports:
                errors.append('{} did not produce the following reports for {}:\n  - {}'.format(
                    simulator, example['filename'], '\n  - '.join(sorted(missing_reports))))
            if extra_reports:
                errors.append('{} produced extra reports for {}:\n  - {}'.format(
                    simulator, example['filename'], '\n  - '.join(sorted(extra_reports))))

            for report in example['reports']:
                report_filename = os.path.join(example_out_dir, report['filename'])
                if not os.path.isfile(report_filename):
                    report_filename = os.path.join(example_out_dir, report['filename'].replace('.sedml', ''))
                if not os.path.isfile(report_filename):
                    errors.append('{} did not produce report {} for {}'.format(simulator, report['filename'], example['filename']))
                    continue

                if simulator in ['amici', 'copasi', 'gillespy2']:
                    df = pandas.read_csv(report_filename, index_col=0, header=None)
                    df.columns = pandas.RangeIndex(start=0, stop=df.shape[1], step=1)
                else:
                    df = pandas.read_csv(report_filename)
                    df = df.transpose()

                if df.shape[0] != report['data_sets']:
                    errors.append('{} produced incorrect number of datasets for {} for {}'.format(
                        simulator, report['filename'], example['filename']))

                if df.shape[1] != report['number_of_points']:
                    errors.append('{} produced incorrect number of time points for {} for {}'.format(
                        simulator, report['filename'], example['filename']))

                if numpy.any(numpy.isnan(df)):
                    errors.append('{} produced incorrect results for {} for {}'.format(simulator, report['filename'], example['filename']))

    if errors:
        raise SystemExit(
            'The simulators did not consistently execute the examples:\n\n  {}'.format(
                '\n\n'.join(errors).replace('\n', '\n  ')))


if __name__ == "__main__":
    run()
