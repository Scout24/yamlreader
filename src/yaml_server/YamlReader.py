'''
Created on Mar 11, 2013

@author: sschapiro
'''

from yaml import MarkedYAMLError, safe_load, safe_dump
import sys
import glob
import os
import logging
from yaml_server.YamlServerException import YamlServerException

def dict_merge(a, b, path=None):
    """merges b into a
    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays and to replace the content of keys with the same name"""
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key].extend(b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


class YamlReader:
    def __init__(self,dir_path):
        self.logger = logging.getLogger(__name__)
        self.data = {}
        files = sorted(glob.glob(os.path.join(dir_path,"*.yaml")))
        if not files:
            raise YamlServerException("No .yaml files found in %s" % dir_path)
        self.logger.debug("Reading %s\n" % ", ".join(files))
        for f in files:
            try:
                new_data = safe_load(file(f))
            except MarkedYAMLError, e:
                raise YamlServerException("YAML Error: %s" % str(e))
            dict_merge(self.data,new_data)
    

    def get(self):
        return self.data
    
    def dump(self):
        return safe_dump(self.data, indent=4, default_flow_style=False, canonical=False)
    

if __name__ == "__main__":
    usage='''YAML Reader merges all .yaml files in a directory given as arg.'''
    print YamlReader(sys.argv[1]).dump()