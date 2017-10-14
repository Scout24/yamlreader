# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

__all__ = ['yaml_load', 'data_merge', 'YamlReaderError']
__version__ = '4.0.0'

import os, sys
#FIXME optparse deprecated in favor of argparse!!
import optparse
import logging
from .yrlogging import *


# see http://yaml.readthedocs.io/en/latest/overview.html
import ruamel.yaml as yaml

__defaults = dict(
        debug = False,
        verbose = False,
        quiet = False,
        ignore_error = True,
        logfile = None,
        log_format = '%(levelname)-8s "%(message)s"',
        log_level = logging.INFO,
        console_format = None,
        console_level = logging.ERROR,
        file_format = None,
        file_level = logging.INFO,
        merge = True,
        no_anchor = True,
        dup_keys = True,
        sort_keys = False,
        sort_files = True, # v3.0 backward-compat
        reverse = False,
        json = False,
        suffix = 'yaml',
        indent = 2,
        loader = 'safe'
    )
options = optparse.Values(__defaults)
options.console_format = '%s: ' % __name__ + options.log_format

yaml_loaders = ['safe', 'base', 'rt', 'unsafe']
#XXX use **dict to convert to kwargs
__yaml_defaults = dict(
        preserve_quotes = True,
        default_flow_style = False,
        # see http://yaml.readthedocs.io/en/latest/detail.html#indentation-of-block-sequences
        indent = {}
    )
#XXX
print("my name is %s" % __name__)
logger = logging.getLogger(__name__)
logger.propagate = False

myaml = None


class YamlReaderError(Exception):
    """write YAML processing errors to logger"""

    #TODO if I was called as a raise, then do super() otherwise stomp on that output since it ends up on STDOUT
    def __init__(self, msg, rc=os.EX_SOFTWARE, level=logging.ERROR): #*args, **kwargs):
        
        # send_to_logger = False

        # for handle in logger.get(handlers):
            # if isinstance(handle, logging.FileHandler):
                # send_to_logger = True
                # break
        # if isinstance(level, str):
            # level = getLevel(level)

        #TODO case statement to generate/modify strings so it's not buried in multiple
        # places in code. eg. 'filenotfound' is easy case. msg == filename(s)
        # TODO invoke via 'raise YamlReaderError(msg, level) from FileNotFoundError'?

        super().__init__(msg)
        frame = sys._getframe().f_back.f_code.co_name
        #TODO break out and differentiate as needed. some raise, others (all?) pass

        if level > logging.CRITICAL or options.ignore_error == False:
            # restore default exception formatting
            sys.excepthook = sys.__excepthook__
            logger.log(level, '%s::%s', frame, msg, exc_info=True)
            # mimic signals.h SIGTERM, or use os.EX_*
            sys.exit(128+rc)
        
        logger.log(level, '%s::%s', frame, msg, exc_info=(options.verbose or options.debug))


def data_merge(a, b, merge=True):
    """merges b into a and return merged result

    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays (append) and dict keys replaced if having the same name.

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen
    """

    import six
    key = None

    #logger.debug('Attempting merge of "%s" into "%s"\n' % (b, a))
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
                for key in b:
                    a[key] = data_merge(a[key], b[key]) if key in a else b[key]
            else:
                # XXX technically a Tuple or List of at least 2 wide
                # could be used with [0] as key, [1] as value
                raise TypeError
        else:
            raise TypeError

    except (TypeError, LookupError) as e:
        raise YamlReaderError('caught %r merging %r into %r\n  "%s" -> "%s"' % 
            (e, type(b), type(a), b, a), logging.WARNING) from e
            # or str(e) also with e.__name__ ?

    return a


def get_files(source, suffix='yaml'):
    """Examine pathspec elements for files to process

    'source' can be a filename, directory, a list/tuple of same,
    or a glob expression with wildcard notion (?*[]).
    If a directory, filenames ending in $suffix will be chosen.
    """
    import os, glob
    files = []

    if source is None or len(source) == 0 or source == '-':
        return ['']

    #if type(source) is list or type(source) is tuple:
    if isinstance(source, list) or isinstance(source, tuple):
        for item in source:
            # iterate to expand list of potential dirs and files
            files.extend(get_files(item, suffix))
        return files

    if os.path.isdir(source):
        files = glob.glob(os.path.join(source, '*.' + suffix))
    elif os.path.isfile(source):
        # turn single file into list
        files = [source]
    else:
        # try to use the source as a glob
        files = glob.glob(source)

    if len(files) == 0:
        # TODO  what is suitable error level?
        # if options.ignore_error , use ERROR, otherwise WARNING
        level = logging.WARNING if options.ignore_error else logging.ERROR
        YamlReaderError('FileNotFoundError for %r' % source,
                rc=os.EX_OSFILE,
                level=level)

    return files


def parse_cmdline():
    """Process command-line options"""

    usage = "%prog [options] source ..."
    parser = optparse.OptionParser(usage, 
                description='Merge YAML/JSON elements from Files, Directories, or Glob pattern',
                version="%" + "prog %s" % __version__, prog='yamlreader')

    parser.disable_interspersed_args()

    parser.add_option('-d', '--debug', dest='debug',
            action='store_true', default=__defaults['debug'],
            help="enable debugging       %default")

    parser.add_option('-v', '--verbose', dest='verbose',
            action='store_true', default=__defaults['verbose'],
            help="extra messages         %default")

    parser.add_option('-q', '--quiet', dest='quiet',
            action='store_true', default=__defaults['quiet'],
            help="minimize output        %default")

    parser.add_option('-c', '--continue', dest='ignore_error',
            action='store_true', default=__defaults['ignore_error'],
            help="errors as not fatal    %default")

    parser.add_option('-l', '--logfile', dest='logfile',
            action='store', default=__defaults['logfile'])

    #TODO log_format = '%(levelname)8s "%(message)s"',

    parser.add_option('--log-level', dest='log_level',
            action='store', default=__defaults['log_level'],
            help=' '.join(logging._nameToLevel.keys()),
            choices=list(logging._nameToLevel.keys()))

    parser.add_option('--console-level', dest='console_level',
            action='store', default=__defaults['console_level'],
            help="                       %default ")

    parser.add_option('--file-level', dest='file_level',
            action='store', default=__defaults['file_level'])

    parser.add_option('-M', '--overwrite', dest='merge',
            action='store_false', default=not __defaults['merge'],
            help="overwrite keys         %default")

    # CloudFormation can't handle anchors or aliases in final output
    parser.add_option('-X', '--no-anchor', dest='no_anchor',
            action='store_true', default=__defaults['no_anchor'],
            help="unroll anchors         %default")

    parser.add_option('-u', '--unique-keys', dest='dup_keys',
            action='store_false', default=__defaults['dup_keys'],
            help="skip duplicates        %default")

    parser.add_option('-k', '--sort-keys', dest='sort_keys',
            action='store_true', default=__defaults['sort_keys'],
            help="sort keys              %default")

    parser.add_option('-S', '--no-sort-files', dest='sort_files',
            action='store_false', default=__defaults['sort_files'],
            help="sort filenames         %default")

    parser.add_option('-r', '--reverse', dest='reverse',
            action='store_true', default=__defaults['reverse'],
            help="sort direction         %default")

    parser.add_option('-j', '--json', dest='json',
            action='store_true', default=__defaults['json'],
            help="output as JSON         %default")

    parser.add_option('--suffix', dest='suffix',
            action='store', default=__defaults['suffix'],
            help="filename suffix        '%default'")

    #TODO - defaults for Yaml constructor.
    # move loader and indent into __yaml_defaults and prepend name with 'yaml'
    parser.add_option('-t', '--indent', dest='indent',
            action='store', type=int, default=__defaults['indent'],
            help="                       %default")

    parser.add_option('--loader', dest='loader',
            action='store', default=__defaults['loader'],
            help="%s    %s" % (' '.join(yaml_loaders), __defaults['loader']),
            choices=yaml_loaders)
# | %default
    try:
        return parser.parse_args()
    #FIXME figure out what to trap
    except Exception as ex:
        parser.error(ex)


def _newYaml():
    #TODO use kwargs or module defaults?
    global myaml
    
    try:
        if not isinstance(myaml, yaml.YAML):
            myaml = yaml.YAML(typ=options.loader)

        # useful defaults for AWS CloudFormation
        myaml.preserve_quotes=True
        myaml.default_flow_style=False
        myaml.allow_duplicate_keys = options.dup_keys
        myaml.representer.ignore_aliases = lambda *args: True

        # see http://yaml.readthedocs.io/en/latest/detail.html#indentation-of-block-sequences
        myaml.indent = dict(
                mapping  = options.indent,
                sequence = options.indent * 2,
                offset   = options.indent
            )
    #FIXME what can YAML() throw? need to catch Math error, possibly Type and ValueError
    except Exception as ex:
        raise YamlReaderError('XXX') from ex


def yaml_load(source, defaultdata=None):
    """merge YAML data from files found in source
    
    Always returns a dict. The files are read with the 'safe' loader
    though the other 3 options are possible.
    
    'source' can be a file, a dir, a list/tuple of files or a string containing
    a glob expression (with ?*[]).
    For a directory, all *.yaml files will be read in alphabetical order.
    """
    global myaml

    logger.debug("yaml_load() initialized with source='%s', defaultdata='%s'", source, defaultdata)
    _newYaml()
        
    # NOTICE - sort_keys is a NOOP unless Matt's version of
    # Ruamel's YAML library (https://bitbucket.org/tb3088/yaml)
    if hasattr(myaml.representer, 'sort_keys'):
        myaml.representer.sort_keys = options.sort_keys

    files = get_files(source, options.suffix)
    if len(files) == 0:
        raise YamlReaderError('FileNotFoundError for %s' % source)
        return None

    data = defaultdata
    for yaml_file in sorted(files, reverse=options.reverse) if options.sort_files else files:
        if options.verbose:
            logger.debug("processing '%s'...", yaml_file)

        try:
            new_data = myaml.load(open(yaml_file) if len(yaml_file) else sys.stdin)
            logger.debug('payload: %r\n', new_data)
        except yaml.MarkedYAMLError as ex:
            YamlReaderError('during YAML.load() of %s' % yaml_file, 
                rc=os.EX_DATAERR, level=getLevel('NOTICE'))
        except:
            #FIXME what to do?
            pass

        if new_data:
            data = data_merge(data, new_data, options.merge)
        elif options.verbose:
        #XXX rc=os.EX_NOINPUT, actually os.EX_DATAERR
            logger.info("no YAML data in %s", yaml_file)

    return data

    
def __main(opts, *argv):
    import json
    global options

    #TODO split varification into separate helper? getting too long.
    try:
        # merge __defaults + user-supplied into 'options'
        if isinstance(opts, optparse.Values):
            kv = vars(opts)
        elif isinstance(opts, dict):
            kv = opts
        elif opts is None:
            kv = {}
        else:
            # too early for YamlReaderError
            raise TypeError("%s not supported for parameter 'opts'" % type(opts))

        print(kv) #XXX

        for k, v in kv.items():
            options.ensure_value(k, v)

        if not (options.log_level and options.log_format):
            raise ValueError('options.log_* can not be blank')
        #TODO check other fields which can't be blank

    except Exception as ex:
        logger.critical("%s while merging 'opts' into 'options'.\n  %r\n  %r", 
                ex.__name__, opts, options)
        return os.EX_CONFIG


    # adjust 'loader' because Ruamel's cryptic short name
    if options.loader == 'roundtrip':
        options.loader = 'rt'

    # normalize logging 'levels' and upcase for downstream lookups
    for attr in (s + '_level' for s in ['log', 'console', 'file']):
        try:
            setattr(options, attr, str.upper(getattr(options,attr)))
        except TypeError:
            pass

    if options.debug:
        options.loglevel = logging.DEBUG    # getLevel('DEBUG')
        # reset to trigger Handler-specific override
        options.console_level = options.file_level = None
        options.verbose = True
        logger.setlevel(logging.DEBUG)
        
    # override/set Handler-specific levels from parent
    if not options.console_level:
        options.console_level = options.log_level
    if not options.file_level:
        options.file_level = options.log_level

    if not options.console_format:
        options.console_format = options.log_format
    if not options.file_format:
        options.file_level = options.log_format

    if not options.quiet:
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(options.console_format))
            console_handler.setLevel(options.console_level)
        except: #FIXME what to trap?
            msg=''
            raise   #TODO logger.error()
            if not options.ignore_error:
                return os.EX_CONFIG
        else:
            logger.addHandler(console_handler)

    if options.logfile:
        try:
            file_handler = logging.FileHandler(options.logfile, mode='w')
            file_handler.setFormatter(logging.Formatter(options.file_format))
            file_handler.setLevel(options.file_level)
        except (FileNotFoundError, OSError): #TODO what else?  rc=os.EX_OSFILE
            options.logfile = None
            msg=''
            raise   #TODO logger.error()
            if options.ignore_error:
                return os.EX_CONFIG
        else:
            logger.addHandler(file_handler)

    # squelch stacktrace if quiet. This affects all handlers, however which
    # wasn't the intent - just keep the console clear and not duplicate
    # exception strings. TODO
    if options.quiet:
        sys.excepthook = lambda *args: None
    elif options.debug:
        pass
    else:
        sys.excepthook = lambda exctype, exc, traceback : print("{}: {}".format(exctype.__name__, exc))


    # Finally ready to do useful work!
    data = yaml_load(argv)
    if data is None or len(data) == 0:
        # a NOOP is not an error, but no point going further
        if option.verbose:
            logger.info('No YAML data found at all!')
        return os.EX_NOINPUT

    try:
        if options.json:
            json.dump(data, sys.stdout, options.indent)
        else:
            myaml.dump(data, sys.stdout)
    #TODO combine logging, no need to raise since no external caller.
    #except yaml.MarkedYAMLError as ex:
    #except (ValueError, OverflowError, TypeError): json.dump()?
    except Exception as ex:
        logger.warning('%s while dump()' % ex.__name__)
        # JSON dump might trigger these
        return os.EX_DATAERR
    
    return os.EX_OK

# if __name__ == '__main__':
    # (opts, args) = parse_cmdline()
    # sys.exit(__main(opts, args))
