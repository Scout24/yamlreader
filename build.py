from __future__ import print_function, absolute_import, unicode_literals, division
from pybuilder.core import use_plugin, init, task, depends, Author

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.coverage")
use_plugin("python.distutils")


name = "yamlreader"
summary = 'Merge YAML data from given files, dir or file glob'
authors = [Author('Schlomo Schapiro', "schlomo.schapiro@immobilienscout24.de")]
url = 'https://github.com/ImmobilienScout24/yamlreader'
version = '3.0.4'
description = open("README.rst").read()
license = 'Apache License 2.0'

default_task = ["clean", "analyze", "publish"]


@init
def set_properties(project):
    project.depends_on("PyYAML")
    project.depends_on("six")

    project.set_property('distutils_console_scripts', ['yamlreader=yamlreader.yamlreader:__main'])

    project.set_property("distutils_classifiers", [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ])


@task
@depends('prepare')
def build_directory(project):
    print(project.expand_path("$dir_dist"))
