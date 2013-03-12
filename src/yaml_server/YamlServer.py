import yaml_server
from yaml_server.YamlLocations import YamlLocations
from yaml_server.YamlServerException import YamlServerException

# ignore popen2 deprecation warning
import warnings
warnings.filterwarnings("ignore")

import SimpleHTTPServer

import logging

import hashlib

class YamlServerRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    
    def __init__(self, *args):
        self.logger = logging.getLogger(__name__)
        # the top-level ancestor (BaseRequestHandler) is NOT a new-style class and does NOT inherit object!
        SimpleHTTPServer.SimpleHTTPRequestHandler.__init__(self, *args)
    
    
    def do_GET(self, onlyHeaders=False):
        '''Serve a GET request'''
        
        status = 500
        content_type = "text/plain"
        if "Range" in self.headers:
            # filter out things that we don't support
            content = "Range header is not supported"
            status = 501
        else:                        
            try:
                if not self.path or self.path == "/":
                    content = yaml_server.__config__["locations"].get_locations_as_yaml()
                else:
                    content = yaml_server.__config__["locations"].get_yaml(self.path[1:])  # get everything from after the /
                # successfully loaded YAML content
                status = 200
                content_type = "application/yaml"
                etag = hashlib.sha256(content).hexdigest()
                etag_header = "If-None-Match"
                if etag_header in self.headers and etag == self.headers.get(etag_header):
                    status = 304
                    content = None
                else:
                    self.send_header("ETag",etag)
                    
            except YamlServerException as e:
                content = e.message
                status = 404 
    
        self.send_response(status)
        if content:
            self.send_header("Content-length", len(content))
            self.send_header("Content-type", content_type)
        self.end_headers()
        
        if not onlyHeaders and content:
            self.wfile.write(content)

    def do_HEAD(self):
        """Serve a HEAD request."""
        self.doGET(True)
        
    def end_headers(self):
        """Send standard headers and end header sending"""
        SimpleHTTPServer.SimpleHTTPRequestHandler.end_headers(self)
        
    def log_message(self, format, *args):
        """Log an arbitrary message.

        This is used by all other logging functions.  Override
        it if you have specific logging wishes.

        The first argument, FORMAT, is a format string for the
        message to be logged.  If the format string contains
        any % escapes requiring parameters, they should be
        specified as subsequent arguments (it's just like
        printf!).

        The client ip address is prefixed to every message.

        """

        self.logger.info("%s %s" % (self.client_address[0], format % args))

    def log_error(self, format, *args):
        """Log an error.

        Arguments are the same as for log_message().

        """

        self.logger.error("%s %s" % (self.client_address[0], format % args))