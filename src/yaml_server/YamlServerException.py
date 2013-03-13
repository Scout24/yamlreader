'''
Created on Mar 11, 2013

@author: sschapiro
'''
class YamlServerException(Exception):
    def __init__(self,message=""):
        self.message=message

    def __str__(self):
        return self.message