import yaml_server
from YamlServer import YamlServerRequestHandler
from YamlServerException import YamlServerException
from YamlReader import YamlReader
from YamlLocations import YamlLocations
from YamlDaemon import YamlDaemon

import os
import sys
import logging
import logging.handlers
import optparse
import SocketServer
import signal
from traceback import print_exception

class YamlServerMain(YamlDaemon):
    def __init__(self,*args,**kwargs):
        usage = '''%prog merges all .yaml files in a directory and exports them over HTTP.'''

        # initialize super class
        YamlDaemon.__init__(self,*args,**kwargs)
    
        self.logger = logging.getLogger()
        self.loghandler = logging.handlers.SysLogHandler(address='/dev/log')
        self.loghandler.setFormatter(logging.Formatter('yaml_server[' + str(os.getpid()) + ']: %(levelname)s: %(message)s'))
        self.logger.addHandler(self.loghandler)
        self.logger.setLevel(logging.INFO)
    
        parser = optparse.OptionParser(usage=usage, version=yaml_server.__version__, prog="yaml_server")
        parser.add_option("--debug", dest="debug", action="store_true", default=False, help="Enable debug logging [%default]")
        parser.add_option("--confdir", dest="confdir", action="store", default="/etc/yaml_server", type="string", help="Directory for configuration files [%default]")
        options, arguments = parser.parse_args()
        if options.debug:
                self.logger.setLevel(logging.DEBUG)
        if arguments:
            self.logger.warning("Ignoring extra command line arguments %s" % ", ".join(arguments))
    
        try:
            yaml_server.__config__ = YamlReader(options.confdir).get()
            self.logger.debug("Configured with %s" % yaml_server.__config__)
            if not ("locations" in yaml_server.__config__ and type(yaml_server.__config__["locations"]) is dict):
                raise YamlServerException("locations key not defined or not a dict")
            yaml_server.__config__["locations"] = YamlLocations(yaml_server.__config__["locations"])
            
            # load port from config
            self.port = yaml_server.__config__.get("port",8935)
            self.pidfile = yaml_server.__config__.get("pidfile","/var/run/yaml_server")
            
            # override log level from config
            if "loglevel" in yaml_server.__config__ and not options.debug:
                # do not change log level from config if debug specified on command line
                self.logger.debug("Setting log level to '%s'" % yaml_server.__config__["loglevel"])
                self.logger.setLevel(yaml_server.__config__["loglevel"])
        except Exception, e:
            self.logger.fatal("Could not initialize yaml_server configuration from %s: %s" % (options.confdir,str(e)))
            sys.exit(1)


    def run(self):
        try:
            httpd = SocketServer.TCPServer(("", yaml_server.__config__["port"]), YamlServerRequestHandler)
        except Exception, e:
            self.logger.fatal("Could not start server: %s" % str(e))
            sys.exit(1)

        try:
            self.drop_privileges(yaml_server.__config__.get("user",None), yaml_server.__config__.get("group",None))
        except Exception, e:
            self.logger.fatal("Could not drop privileges: %s" % str(e))
            sys.exit(1)


        self.logger.info("Starting on port %s for %s" % (self.port, yaml_server.__config__["locations"].locations))
        try:
            def shutdown_func(*args):
                self.logger.debug("Shutdown")
                httpd.socket.close()
                # httpd.shutdown() TODO: Find out why this does not work!
                self.logger.debug("Shutdown done")
                raise SystemExit(0)
            # register proper kill handlers so that we can be killed cleanly
            signal.signal(signal.SIGINT,shutdown_func)
            signal.signal(signal.SIGTERM,shutdown_func)
            # long poll to be nice to the system ressources. This is fine as long as httpd.shutdown() does not work for us. See SocketServer for details.
            httpd.serve_forever()
        except SystemExit:
            pass
        except Exception, e:
            self.logger.debug("Unexpeted Shutdown: %s" % str(e))
            from traceback import print_exc
            print_exc(file=sys.stderr)
    
