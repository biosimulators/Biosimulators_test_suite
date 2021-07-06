#!/usr/bin/env python

"""
Zip example COMBINE/OMEX archives from directories

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2021-07-06
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

import glob
import os
import subprocess
import zipfile


def main():
    examples_dirname = os.path.join(os.path.dirname(__file__), '..', 'examples')
    for archive_dirname in glob.glob(os.path.join(examples_dirname, '**', '*')):
        if os.path.isdir(archive_dirname):
            archive_filename = archive_dirname + '.omex'

            if os.path.isfile(archive_filename):
                with zipfile.ZipFile(archive_filename, mode='r') as zip_file:
                    cur_archive_names = zip_file.namelist()

            archive_names = [
                os.path.relpath(filename, archive_dirname)
                for filename in glob.glob(os.path.join(archive_dirname, '**', "*"), recursive=True)
                if os.path.isfile(filename)
            ]

            if set(cur_archive_names) != set(archive_names):
                os.remove(archive_filename)

            for archive_name in archive_names:
                cmd = ['zip', '-ur', os.path.relpath(archive_filename, archive_dirname), archive_name]
                result = subprocess.run(cmd, cwd=archive_dirname, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if result.returncode not in [0, 12]:
                    raise ValueError(result.stdout.decode(errors='ignore'))


if __name__ == "__main__":
    main()
