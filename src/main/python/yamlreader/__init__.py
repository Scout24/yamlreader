# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

__all__ = ['yaml_load', 'data_merge', 'YamlReaderError']
__version__ = '4.0.0'

import os, sys
#FIXME optparse deprecated in favor of argparse!!
import optparse
import logging
# define missing syslog(3) levels and also handy helpers
logging.addLevelName(logging.DEBUG - 5, 'TRACE')
logging.addLevelName(logging.INFO + 5, 'NOTICE')
# fix Lib/logging improperly conflating CRITICAL and FATAL
logging.addLevelName(logging.CRITICAL + 1, 'FATAL')
logging.addLevelName(logging.CRITICAL + 10, 'ALERT')
logging.addLevelName(logging.CRITICAL + 20, 'EMERG')
logging.addLevelName(99, 'ABORT')

# see http://yaml.readthedocs.io/en/latest/overview.html
import ruamel.yaml as yaml
from .yrlogging import getLevel #, getLevelName

#FIXME everything that isn't 'main' 
#FIXME putthis mostly back into main.py, 
# the class methods can log. myaml being a class global is fine too.
# options can stay, console_format needs to move to main().

__yaml_loaders = ['safe', 'roundtrip', 'unsafe']
__defaults = dict(
        debug = False,
        verbose = False,
        quiet = False,

        console_format = '%s: ' % __name__ + '%(levelname)-8s "%(message)s"',
        console_level = logging.WARNING,
        logfile_format = '%(levelname)-8s "%(message)s"',
        logfile_level = logging.INFO,
        logfile = None,

        merge = True,
        anchors = False,
        allow_duplicate_keys = True,
        sort_keys = False,
        sort_files = True, # v3.0 backward-compat
        reverse = False,
        json = False,
        suffix = '',
        recurse = False,
        indent = 2,
        loader = 'safe'
    )

options = optparse.Values(__defaults)
#options.console_format = '%s: ' % __name__ + options.log_format

#TODO there's a way to detect teh 'debug' or 'verbose' flags that the parser was called with.
# sys.flags.debug, optimize, verbose and quiet. https://docs.python.org/3.3/library/sys.html

logger = logging.getLogger(__name__)
logger.propagate = False

#TODO refactor the options checking for logging to separate method
# and key off of logger.hasHandlers() = False inside yaml_load() and __main() to initialize
logger.setLevel(logging.INFO)


#TODO rename to '_yaml' or 'readerYaml' or figure out a way to pass it around WITHOUT it being a global
myaml = None


class YamlReaderError(Exception):
# the *ONLY* exception being raised out of this class should be this.
#TODO rename to ...Exception for more obviousness? plus the level being dealt with isn't necessary just ERROR.
    """write YAML processing errors to logger"""

    def __init__(self, msg, level=logging.ERROR, rc=os.EX_SOFTWARE): #*args, **kwargs):

        # for handle in logger.get(handlers):
            # if isinstance(handle, logging.FileHandler):
                # send_to_logger = True
                # break
        #TODO check/rationalize log level.
        if isinstance(level, str):
            level = getLevel(level)

        #TODO case statement to generate/modify strings so it's not buried in multiple
        # places in code. eg. 'filenotfound' is easy case. msg == filename(s)
        # TODO invoke via 'raise YamlReaderError(msg, level) from FileNotFoundError'?

        super().__init__(msg)
        frame = sys._getframe().f_back.f_code.co_name

        if not options.quiet:
            # don't use logger.exception() because handling it ourself
            logger.log(level, '%s::%s', frame, msg, exc_info=(options.verbose or options.debug))

        if level > logging.CRITICAL and not options.ignore_error:
                #if options.quiet:
                # raises SystemExit and invokes any 'finally' clauses
                # if untrapped, the Python interpreter exits; no stack traceback is printed.
                # mimic signals.h SIGTERM, or use os.EX_*
                sys.exit(128+rc)
                # else:
                    # restore default exception formatting?
                    # sys.excepthook = sys.__excepthook__


def data_merge(a, b, merge=True):
    """merges b into a and return merged result

    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays (append) and dict keys replaced if having the same name.

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen
    """
    import six
    logger.debug('Attempt data_merge() of\n\t"%s"\n  into\n\t"%s"\n' % (b, a))

    try:
        # border case for first run or if a is a primitive
        if a is None or isinstance(a, (six.string_types, float, six.integer_types)):
            a = b
        elif isinstance(a, list):
            a.extend(b) if isinstance(b, list) else a.append(b)
            a = list(set(a))
        elif isinstance(a, dict):
            if not merge:
                a.update(b)
            elif isinstance(b, dict):
                for key in b.keys():
                    if key in a:
                        a[key] = data_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                # TODO technically a Tuple or List of at least 2 wide
                # could be used with [0] as key, [1] as value
                raise TypeError
        else:
            raise TypeError

    except (TypeError, LookupError) as ex:
        logger.warning('caught %s:(%s) while data_merge()' % (type(ex).__name__, ex))
        logger.debug('data_merge(): "%s" -> "%s"' % (b, a))
        #FIXME do we really want to emit this here? use raise or just log? 
        # raise YamlReaderError('caught %s (%s) merging %r into %r\n  "%s" -> "%s"' %
                # (type(ex).__name__, ex, type(b), type(a), b, a), from ex

    return a


def get_files(source, suffix='', recurse=False):
    """Examine pathspec elements for files to process

    'source' can be a filename, directory, a list/tuple of same,
    or a glob expression with wildcard notion (?*[]).
    If a directory, filenames ending in $suffix will be chosen.
    """
    import os, glob
    files = []

    if source is None or len(source) == 0 or source == '-':
        files = ['']
        return files

    if isinstance(source, list) or isinstance(source, tuple):
        for item in source:
            # iterate to expand list of potential dirs and files
            files.extend(get_files(item, suffix))
        return files

    if os.path.isdir(source):
        files = glob.glob(os.path.join(source, '*' + suffix))
    elif os.path.isfile(source):
        # turn single file into list
        files = [source]
    else:
        # TODO??? change to iglob() and accept only '*suffix'?
        files = glob.glob(source, recursive=recurse)

    return files


def _newYaml(preserve_quotes=True, default_flow_style=False, indent=None):
    #FIXME should be 'settings' which map to Yaml internals directly
    # ala for key in settings.keys() myaml.key = settings[key]
    # handle special case that is 'indent'
    global myaml

    try:
        myaml = yaml.YAML(typ=options.loader)

        # useful defaults for AWS CloudFormation
        myaml.preserve_quotes=preserve_quotes
        myaml.default_flow_style=default_flow_style
        myaml.allow_duplicate_keys = options.allow_duplicate_keys
        if not options.anchors:
            myaml.representer.ignore_aliases = lambda *args: True

        # see http://yaml.readthedocs.io/en/latest/detail.html#indentation-of-block-sequences
        #TODO update indents based on options.indent if parameter is None? Do we assume {} means no indent?
        if isinstance(indent, dict):
            # TODO seq >= offset+2 
            myaml.indent(mapping=indent['mapping'], offset=indent['offset'], sequence = indent['sequence'])
        elif isinstance(int, indent):
            myaml.indent(indent)
        #else: TODO throw something?

    #FIXME what can YAML() throw? need to catch Math error, possibly Type and ValueError
    # ??AttributeError when calling constructors
    except KeyError:
        # ignore 
        pass
    except Exception as ex:
        #TODO
        raise YamlReaderError('XXX') from ex


def yaml_load(source, data=None,
        preserve_quotes=True, default_flow_style=False, 
        indent=dict(mapping=options.indent, sequence=options.indent, offset=0)):
    #TODO pass in a pre-instantiated YAML class object so any 3rd party (API compat)
    """merge YAML data from files found in source

    Always returns a dict. The files are read with the 'safe' loader
    though the other 3 options are possible.

    'source' can be a file, a dir, a list/tuple of files or a string containing
    a glob expression (with ?*[]).
    For a directory, all *.yaml files will be read in alphabetical order.
    """
    global myaml

    logger.log(getLevel('TRACE'), "yaml_load() called with\n\tsource='%s'\n\tdata='%s'", source, data)
    #TODO bring _newYaml back here, it's not THAT long.
    # assume already configured
    if not isinstance(myaml, yaml.YAML):
        _newYaml(preserve_quotes, default_flow_style, indent)

    # NOTICE - sort_keys is a NOOP unless Matt's version of
    # Ruamel's YAML library (https://bitbucket.org/tb3088/yaml)
    if hasattr(myaml.representer, 'sort_keys'):
        myaml.representer.sort_keys = options.sort_keys

    files = get_files(source, options.suffix, options.recurse)
    if len(files) == 0:
        raise YamlReaderError("FileNotFoundError for %s" % source, rc=os.EX_OSFILE)
        # from FileNotFoundError("%s" % source)
        # from YamlReaderError("FileNotFoundError for %s" % source, rc=os.EX_OSFILE)

    new_data = None
    for yaml_file in sorted(files, reverse=options.reverse) if options.sort_files else files:
        logger.info("processing '%s' ...", yaml_file)

        try:
            new_data = myaml.load(open(yaml_file) if len(yaml_file) else sys.stdin)
        except (yaml.error.YAMLError, yaml.error.YAMLStreamError) as ex:
            raise YamlReaderError("%s during YAML.load()" % ex, rc=os.EX_DATAERR)

        except (yaml.error.YAMLWarning, yaml.error.YAMLFutureWarning) as ex:
            if options.verbose:
                logger.warning("%s during YAML.load()", type(ex).__name__)
            logger.log(getLevel('NOTICE'), "%s", ex)
            # Ruamel throws this despite allow_duplicate_keys?
        except Exception as ex:
            #FIXME stuff from open(), data_merge()
            # just silently squelch everything but MarkedYAML?
            logger.warning("unhandled %s during YAML.load() of '%s'" % (type(ex).__name__, yaml_file))
            if not options.ignore_error:
                raise

        if new_data:
            logger.debug('payload: %r\n', new_data)
            data = data_merge(data, new_data, options.merge)
        else:
            logger.log(getLevel('NOTICE'), "no payload found in '%s'", yaml_file)

    return data
    

def parse_cmdline():
    """Process command-line options"""
    usage = "%prog [options] source ..."

    #FIXME replace with argparse class
    parser = optparse.OptionParser(usage,
                description='Merge YAML/JSON elements from Files, Directories, or Glob pattern',
                version="%" + "prog %s" % __version__, prog='yamlreader')

    parser.disable_interspersed_args()

    parser.add_option('-d', '--debug', dest='debug',
            action='store_true', default=__defaults['debug'],
            help='%-35s %s' % ('enable debugging', "%default"))

    parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=__defaults['verbose'],
            help='%-35s %s' % ('extra messages', "%default"))

    parser.add_option('-q', '--quiet', dest='quiet',
            action='store_true', default=__defaults['quiet'],
            help='%-35s %s' % ('minimize output', "%default"))

    # only useful if invoked via __main__
    parser.add_option('-c', '--continue', dest='ignore_error',
            action='store_true', default=False,
            help='%-35s %s' % ('even if >CRITICAL', "%default"))

    parser.add_option('-l', '--logfile', dest='logfile',
            action='store', default=__defaults['logfile'])

    #TODO log_format = '%(levelname)8s "%(message)s"',

    #FIXME, using _levelToName is cheating
    levels=list(logging._nameToLevel.keys())
    levelstr, i = ('', 1)
    for lev in sorted(logging._levelToName.keys()):
        levelstr += '%s:%d ' % (logging._levelToName[lev], lev)
        # if (i % 4) == 0:
          # levelstr += '\n' # TODO escape sequences gets lost on output
        # i+=1
    # fake entry just for Help
    parser.add_option('--xxx-level',
            action='store_const', const=logging.INFO,
            help='%s' % (levelstr))

    parser.add_option('--console-level', dest='console_level',
            action='store', default=__defaults['console_level'],
            help='%-35s %s' % ('', 
                logging._levelToName.get(__defaults['console_level'])),
            choices=levels)

    parser.add_option('--file-level', dest='logfile_level',
            action='store', default=__defaults['logfile_level'],
            help='%-35s %s' % ('',
                logging._levelToName.get(__defaults['logfile_level'])),
            choices=levels)

    # CloudFormation can't handle anchors or aliases in final output
    parser.add_option('-x', dest='anchors',
            action='store_true', default=__defaults['anchors'],
            help='%-35s %s' % ('preserve anchors/aliases', "%default"))

    parser.add_option('-M', '--overwrite', dest='merge',
            action='store_false', default=__defaults['merge'],
            help='%-35s %s' % ('overwrite keys (last win)', "%default"))

#FIXME is the sense correct? does it effect Merge in practical terms? aka if dup = false, it just skips the merge? 
# as opposed to merge=false means overwrite.
# this nullifies merge in either state.
    parser.add_option('-U', '--unique-keys', dest='allow_duplicate_keys',
            action='store_false', default=not __defaults['allow_duplicate_keys'],
            help='%-35s %s' % ('skip duplicate keys (first win)', "%default"))

    parser.add_option('-k', '--sort-keys', dest='sort_keys',
            action='store_true', default=__defaults['sort_keys'],
            help='%-35s %s' % ('sort keys', "%default"))

    parser.add_option('-S', '--no-sort-files', dest='sort_files',
            action='store_false', default=__defaults['sort_files'],
            help='%-35s %s' % ('sort filenames', "%default"))

    parser.add_option('-r', '--reverse', dest='reverse',
            action='store_true', default=__defaults['reverse'],
            help='%-35s %s' % ('sort direction', "%default"))

    parser.add_option('-j', '--json', dest='json',
            action='store_true', default=__defaults['json'],
            help='%-35s %s' % ('output as JSON', "%default"))

    parser.add_option('--suffix', dest='suffix',
            action='store', default=__defaults['suffix'],
            help='%-35s %s' % ("if dir|glob() apply filter '*suffix'", "%default"))

    parser.add_option('--recurse', dest='recurse',
            action='store_true', default=__defaults['recurse'],
            help='%-35s %s' % ("expand '**' in filespec", "%default"))

    #TODO - defaults for Yaml constructor.
    parser.add_option('-t', '--indent', dest='indent',
            action='store', type=int, default=__defaults['indent'],
            help='%-35s %s' % ('', "%default"))

    parser.add_option('--loader', dest='loader',
            action='store', default=__defaults['loader'],
            help='%-35s %s' % (' '.join(__yaml_loaders), __defaults['loader']),
            choices=__yaml_loaders)
# | %default
    try:
        return parser.parse_args()
    #FIXME figure out what to trap
    except Exception as ex:
        parser.error(ex)


def _configure():
    pass

def __main(opts, *argv):
    global options
    global logger

    try:
        if isinstance(opts, optparse.Values):
            new = vars(opts)
        elif isinstance(opts, dict):
            new = opts
        elif opts is None:
            new = {}
        else:
            # too early for YamlReaderError
            logging.lastResort("Type '%s' not supported for 'opts'" % type(opts))
            return os.EX_CONFIG

        vars(options).update(new)

    except Exception as ex:
        logging.lastResort("caught %s (%s) while merging options" % (type(ex).__name__, ex))
        return os.EX_CONFIG

#FIXME this section belong in _configure which sets up loghandlers
# and is called from yaml_load() if it detects it's not setup.
# eg. if options isnot of type or myaml is not of proper type


#XXX FIXME this whole block needs to be called from _configure as part of main class.

    # normalize logging 'levels' and upcase for downstream lookups
    # gratuitous since optparse() is enforcing values?
    for attr in (s + '_level' for s in ['console', 'logfile']):
        try:
            level = getattr(options, attr)
            if isinstance(level, str):
                # FIXME more cheating
                setattr(options, attr, logger._nameToLevel[str.upper(level)])
            if logging._levelToName[getattr(options, attr)] is None:
                # failsafe
                setattr(options, attr, logging.INFO)
        except (AttributeError, TypeError, ValueError) as ex:
            logging.lastResort("'%s'(%s) during logging failsafe" % (type(ex).__name__, ex))
            if not options.ignore_error:
                return os.EX_CONFIG

    if options.verbose:
        options.console_level=logging.INFO

    if options.debug:
        logger.setLevel(logging.DEBUG)
        options.console_level = logging.DEBUG
        options.logfile_level = logging.DEBUG #TODO getLevel('TRACE') 
        options.verbose = True
        options.quiet = False

    if not options.quiet:
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(options.console_format))
            console_handler.setLevel(options.console_level)
            logger.addHandler(console_handler)
        except Exception as ex: #FIXME what to trap?
            logging.lastResort("%s (%s) configuring console_handler" % (type(ex).__name__, ex))
            if not options.ignore_error:
                return os.EX_CONFIG
        
    if options.logfile:
        try:
            file_handler = logging.FileHandler(options.logfile, mode='w')
            file_handler.setFormatter(logging.Formatter(options.logfile_format))
            file_handler.setLevel(options.logfile_level)
            logger.addHandler(file_handler)
        except (FileNotFoundError, OSError) as ex: #TODO what else?
            options.logfile = None
            logging.lastResort("%s (%s) configuring file_handler" % (type(ex).__name__, ex, options.logfile))
            if not options.ignore_error:
                return os.EX_OSFILE

    # for 'quiet' one could removeHandler(console) but if there are NO
    # handlers Logging helpfully provides one (stderr, level=WARNING)
    if options.quiet:
        if not logger.hasHandlers():
            logger.addHandler(logging.NullHandler())
        # gratuitous? since sys.exit() squelches stacktrace
        sys.excepthook = lambda *args: None
    elif options.debug:
        pass
    else:
        sys.excepthook = lambda exctype, exc, traceback : print("uncaught! {}: {}".format(exctype.__name__, exc))

    # FINALLY logging is ready!

    #TODO split varification into separate configure() helper? getting too long.
    #TODO check other fields which can't be left blank and have no defaults
    
    #TODO handle case of 'batching' files, say process them individually. and emit as multi-doc yaml.
    # is there a method for JSON? I don't think so.

    # HACK 'safe' loader mangles anchors by generating new IDs.
    if options.anchors: # and options.original_anchors:
        options.loader = 'rt'

    # adjust 'loader' because Ruamel's cryptic short name
    if options.loader == 'roundtrip':
        options.loader = 'rt'

    # Finally ready to do useful work!
    #FIXME deal with YamlReaderError getting thrown. from say no input files.
    try:
        data = yaml_load(argv)

        if data is None or len(data) == 0:
        # empty is not an error, but no point going further
            if options.verbose:
                logger.warning('No YAML data anywhere!')
            return os.EX_NOINPUT

#    try:
        if options.json:
            import json
            # JSON is hard to read at less than 4 spaces
            json.dump(data, sys.stdout, indent=options.indent * 2 if options.indent < 4 else options.indent)
        else:
            myaml.dump(data, sys.stdout)

    # except SystemExit:
        # raise
    except YamlReaderError as ex:
        pass
        # eg. argv was invalid
        # TODO take action? no way to know what teh os.EX_ value is...

    #TODO combine logging, no need to raise since no external caller.
    #except yaml.MarkedYAMLError as ex:
    #except (ValueError, OverflowError, TypeError): json.dump()?
    except Exception as ex:
        # JSON dump might trigger these
        logger.error('caught %s (%s) while main()' % (type(ex).__name__, ex))
        return os.EX_DATAERR

    else:
        return os.EX_OK
