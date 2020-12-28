""" Configuration

:Author: Jonathan Karr <karr@mssm.edu>
:Date: 2020-12-28
:Copyright: 2020, Center for Reproducible Biomedical Modeling
:License: MIT
"""

__all__ = ['TERMINAL_COLORS']

TERMINAL_COLORS = {
    'pass': 'green',
    'passed': 'green',
    'failure': 'red',
    'failed': 'red',
    'skip': 'magenta',
    'skipped': 'magenta',
    'warning': 'yellow',
    'warned': 'yellow',
}
