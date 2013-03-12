'''
Created on Mar 11, 2013

@author: sschapiro
'''

from YamlReader import YamlReader
from YamlServerException import YamlServerException
import yaml
import os
import logging

class YamlLocations:
    def __init__(self,locations):
        self.locations = {}
        self.logger = logging.getLogger(__name__)
        for (key,loc_data) in locations.items():
            if not "path" in loc_data:
                raise YamlServerException("No path key given in '%s' location" % key)
            p = loc_data["path"].rstrip("/")
            if os.path.isdir(p):
                self.locations[key] = p
            else:
                self.logger.debug("Skipping invalid directory '%s'" % p)
        if not len(self.locations) > 0:
            raise YamlServerException("No locations configured")

    def get_yaml(self,location):
        if location in self.locations:
            return YamlReader(self.locations[location]).dump()
        else:
            raise YamlServerException("No configuration found for %s" % location)

    def get_locations(self):
        return self.locations.keys()

    def get_locations_as_yaml(self):
        return yaml.safe_dump({"locations" : self.get_locations()}, default_flow_style=False, canonical=False)