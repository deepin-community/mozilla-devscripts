#!/usr/bin/python2

import glob
import os
import re

from distutils.core import setup


def get_debian_version():
    """look what Debian version we have"""
    version = None
    changelog = "debian/changelog"
    if os.path.exists(changelog):
        head = open(changelog).readline()
        match = re.compile(r".*\((.*)\).*").match(head)
        if match:
            version = match.group(1)
    return version


SCRIPTS = [
    'dh_xul-ext',
    'install-xpi',
    'xpi-pack',
    'xpi-unpack',
    'moz-version',
]

# need to treat these separately, else setuptools fucks with the shebang lines
PY3_SCRIPTS = [
    'amo-changelog',
    'dh_webext',
    'xpi-repack',
]

if __name__ == '__main__':
    setup(
        name='mozilla-devscripts',
        version=get_debian_version(),
        scripts=SCRIPTS,
        py_modules=['moz_version'],
        data_files=[
            ('bin', PY3_SCRIPTS),
            ('share/doc/mozilla-devscripts', ['README']),
            ('share/man/man1', glob.glob("man/*.1")),
            ('share/mozilla-devscripts', ['data/xpi.mk'] + glob.glob('data/xul-app-data.csv.*')),
            ('share/perl5/Debian/Debhelper/Buildsystem', ['perl/Debian/Buildsystem/xul_ext.pm']),
            ('share/perl5/Debian/Debhelper/Sequence',
             ['perl/Debian/Sequence/xul_ext.pm', 'perl/Debian/Sequence/webext.pm']),
        ],
    )
