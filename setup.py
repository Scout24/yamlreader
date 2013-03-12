#!/usr/bin/env python

from setuptools import setup, find_packages
import sys
sys.path.insert(0, "src")
from yaml_server import __version__
sys.path.pop(0)
from distutils.command.clean import clean
import os
import shutil

class completeClean(clean):
    def run(self):
        if os.path.exists(self.build_base):
            shutil.rmtree(self.build_base)
            
        dist_dir = 'dist'
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
        dist_dir = "deb_dist"
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
        

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
    long_description="Small Python script that exports YAML configuration directories via HTTP",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Programming Language :: Python",
        ],
    scripts = ["src/bin/yaml_server"],
    data_files=[
                ('/etc/yaml_server', [
                                      'src/conf/00_default.yaml'
                                      ]
                 )
                ],
     cmdclass={'clean' : completeClean},
)
