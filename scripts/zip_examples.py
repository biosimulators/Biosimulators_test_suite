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
import tempfile
import zipfile


def main():
    examples_dirname = os.path.join(os.path.dirname(__file__), '..', 'examples')
    archive_dirnames = [archive_dirname for archive_dirname in glob.glob(os.path.join(examples_dirname, '**', '*'))
                        if os.path.isdir(archive_dirname)]
    for i_archive, archive_dirname in enumerate(archive_dirnames):
        archive_filename = archive_dirname + '.omex'

        fid, temp_archive_filename = tempfile.mkstemp(dir=archive_dirname, suffix='.omex')
        os.close(fid)

        archive_contents = os.walk(archive_dirname)
        with zipfile.ZipFile(temp_archive_filename, 'w') as zip_file:
            for root, dirs, files in archive_contents:
                for file in files:
                    if os.path.abspath(os.path.join(root, file)) != temp_archive_filename:
                        zip_file.write(os.path.join(root, file),
                                       os.path.relpath(os.path.join(root, file),
                                                       archive_dirname))

        if os.path.isfile(archive_filename):
            result = subprocess.run(['zipcmp', temp_archive_filename, archive_filename],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode == 0:
                os.remove(temp_archive_filename)
            else:
                os.rename(temp_archive_filename, archive_filename)
        else:
            os.rename(temp_archive_filename, archive_filename)


def zip_dir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file),
                       os.path.relpath(os.path.join(root, file),
                                       os.path.join(path, '..')))


if __name__ == "__main__":
    main()
