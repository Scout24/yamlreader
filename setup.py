#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
sys.path.insert(0, "src")
from yaml_server import __version__
sys.path.pop(0)

setup(
    name="yaml_server",
    version=__version__,
    author="Schlomo Schapiro & Arkadiusz Dziewonski",
    description="Merge all YAML files in a directory and export result via HTTP",
    license="GPL",
    keywords="yaml export http",
    url="https://github.com/ImmobilienScout24/yaml-server",
    packages=[ "yaml_server" ],
    package_dir={'':'src'},
    package_data={'': ['conf/*']},
    include_package_data=True,
    long_description="Small Python script that exports YAML configuration directories via HTTP",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Programming Language :: Python",
        ],
    entry_points={
        'console_scripts': [
            'yaml_server = yaml_server:__main__',
            ],
        },
    data_files=[
                ('/etc/yaml_server', [
                                      'res/yaml_server/00_default.yaml'
                                      ]
                 )
                ]
)
