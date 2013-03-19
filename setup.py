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

# for RPM we use a classic init script and for DEB we use an upstart service
myScript = ()
cmdline = " ".join(sys.argv).lower()
# do we build for rpm? we find that by parsing the setup.py command line for typical rpm or rpmbuild stuff
if (# rpm in command line
    cmdline.find("rpm") >= 0
    # buildroot in command line
    or cmdline.find("/buildroot") >= 0
    # there is an environment variable that contains rpm in the variable name
    or " ".join(os.environ.keys()).lower().find("rpm") >= 0
    ):
    print "Using runlevel script"
    myScript = ('/etc/init.d', [
                                      'src/init.d/yaml_server'
                                      ]
                 )
else:
    print "Using upstart service"
    myScript = ('/etc/init', [
                                      'src/init/yaml_server.conf'
                                      ]
                 )

setup(
    name="yaml_server",
    version=__version__,
    author="Schlomo Schapiro & Arkadiusz Dziewonski",
    author_email='schlomo.schapiro@immobilienscout24.de',
    description="Merge all YAML files in a directory and export result via HTTP",
    license="GPL",
    keywords="yaml export http",
    url="https://github.com/ImmobilienScout24/yaml-server",
    requires=["yaml"],
    packages=[ "yaml_server" ],
    test_suite="test",
    package_dir={'':'src'},
    long_description="Small Python script that exports YAML configuration directories via HTTP",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Programming Language :: Python",
        ],
    scripts=["src/bin/yaml_server"],
    data_files=[
                ('/etc/yaml_server', [
                                      'src/conf/00_default.yaml'
                                      ]
                 ), myScript
                ],
     cmdclass={'clean' : completeClean},
)
