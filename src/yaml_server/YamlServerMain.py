import yaml_server
from YamlServer import YamlServerRequestHandler
from YamlServerException import YamlServerException
from YamlReader import YamlReader
from YamlLocations import YamlLocations


import os
import sys
import logging
import logging.handlers
import optparse
import SocketServer
import signal

def main():
    usage = '''%prog merges all .yaml files in a directory and exports them over HTTP.'''


    root_logger = logging.getLogger()
    handler = logging.handlers.SysLogHandler(address='/dev/log')
    handler.setFormatter(logging.Formatter('yaml_server[' + str(os.getpid()) + ']: %(levelname)s: %(message)s'))
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    parser = optparse.OptionParser(usage=usage, version=yaml_server.__version__, prog=__package__)
    parser.add_option("--debug", dest="debug", action="store_true", default=False, help="Enable debug logging [%default]")
    parser.add_option("--confdir", dest="confdir", action="store", default="/etc/yaml_server", type="string", help="Directory for configuration files [%default]")
    options, arguments = parser.parse_args()
    if options.debug:
            root_logger.setLevel(logging.DEBUG)
    if arguments:
        root_logger.warning("Ignoring extra command line arguments %s" % ", ".join(arguments))

    try:
        yaml_server.__config__ = YamlReader(options.confdir).get()
        root_logger.debug("Configured with %s" % yaml_server.__config__)
        if not ("locations" in yaml_server.__config__ and type(yaml_server.__config__["locations"]) is dict):
            raise YamlServerException("locations key not defined or not a dict")
        yaml_server.__config__["locations"] = YamlLocations(yaml_server.__config__["locations"])
        
        # override port from config
        if not "port" in yaml_server.__config__:
            yaml_server.__config__["port"] = 8935

        # override log level from config
        if "loglevel" in yaml_server.__config__:
            root_logger.debug("Setting log level to '%s'" % yaml_server.__config__["loglevel"])
            root_logger.setLevel(yaml_server.__config__["loglevel"])

    except BaseException as e:
        root_logger.fatal("Could not initialize yaml_server configuration from %s: %s" % (options.confdir,str(e)))
        sys.exit(1)
    try:
        httpd = SocketServer.TCPServer(("", yaml_server.__config__["port"]), YamlServerRequestHandler)
    except Exception as e:
        root_logger.fatal("Could not start server: %s" % str(e))
        sys.exit(1)

    root_logger.info("Starting on port %s for %s" % (yaml_server.__config__["port"], yaml_server.__config__["locations"].locations))
    try:
        def shutdown_func(*args):
            root_logger.debug("Shutdown")
            httpd.socket.close()
            # httpd.shutdown() TODO: Find out why this does not work!
            root_logger.debug("Shutdown done")
            raise SystemExit(0)
        # register proper kill handlers so that we can be killed cleanly
        signal.signal(signal.SIGINT,shutdown_func)
        signal.signal(signal.SIGTERM,shutdown_func)
        # long poll to be nice to the system ressources. This is fine as long as httpd.shutdown() does not work for us. See SocketServer for details.
        httpd.serve_forever(1000)
    except SystemExit:
        pass
    except BaseException as e:
        root_logger.debug("Unexpeted Shutdown: %s" % e.__repr__())
    except:
        # if there is something we did not catch
        raise

