#!env python3

from __future__ import print_function, absolute_import, unicode_literals, division

__version__ = '3.1.0'

import ruamel.yaml as yaml
import json
import glob
import os
import sys
import logging
import six

logger = logging.getLogger(__name__)


class YamlReaderError(Exception):
    """write YAML processing errors to logger"""
    #TODO if I was called as a raise, then do super() otherwise stomp on that output since it ends up on STDOUT
    def __init__(self, msg, *args, **kwargs):
        level = logging.ERROR

        if args:
          level = args[0].upper() if isinstance(args[0], str) else args[0]
        #TODO case statement to generate/modify strings so it's not buried in multiple
        # places in code. eg. 'filenotfound' is easy case. msg == filename(s)
        # try:
        super().__init__(msg)
        logger.log(level, '%s::%s', sys._getframe().f_back.f_code.co_name, msg,
            exc_info=(logger.getEffectiveLevel() == logging.DEBUG), **kwargs)

        if (level == logging.FATAL):
            sys.exit(1)

        #TODO break out and differentiate as needed. some raise, others (all?) pass
        pass


def data_merge(a, b, merge=True):
    """merges b into a and return merged result

    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays (append) and dict keys replaced if having the same name.

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen
    """
    key = None

    #logger.debug('Attempting merge of "%s" into "%s"\n' % (b, a))
    try:
        # border case for first run or if a is a primitive
        if a is None or merge == False or \
                isinstance(a, (six.string_types, float, six.integer_types)):
            a = b
        elif isinstance(a, list):
            a.extend(b) if isinstance(b, list) else a.append(b)
            a = list(set(a))
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    a[key] = data_merge(a[key], b[key]) if key in a else b[key]
            else:
                raise TypeError
        else:
            raise TypeError

    except (TypeError, LookupError) as e:
        raise YamlReaderError('caught %r merging %r into %r\n  "%s" -> "%s"' % 
            (e, type(b), type(a), b, a), logging.WARNING)
            # or str(e) also with e.__name__ ?

    return a


def get_files(source, suffix='yaml'):
    """Examine path elements for files to processing

    source can be a file, a directory, a list/tuple of files or
    a string containing a glob expression (with ?*[]).

    For a directory, filenames of $suffix will be read.
    """

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
        YamlReaderError('FileNotFoundError for %r' % (source), logging.WARNING)

    return files


def __main():
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] source ...",
                                   description='Merge YAML data from files, directory or glob',
                                   version="%" + "prog %s" % __version__,
                                   prog='yamlreader')

    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False,
                      help="Enable debug logging   (true *%default*)")
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False,
                      help="write progress         (true *%default*)")

    parser.add_option('-l', '--logfile', dest='logfile', action='store', default=None)
    parser.add_option('--log', dest='loglevel', action='store', default='INFO',
                      help="(DEBUG *%default WARNING ERROR CRITICAL)")

    parser.add_option('-j', '--json', dest='json', action='store_true', default=False,
                      help="output to JSON (true *%default)")
    parser.add_option('-m', '--merge', dest='merge', action='store_true', default=True,
                      help="merge a key's values (*%default false)")
    parser.add_option('--overwrite', dest='merge', action='store_false',
                      help="overwrite a key's values (true *false)")
                      # CloudFormation can't handle anchors or aliases (sep '17)
    parser.add_option('-x', '--no-anchor', dest='no_anchor', action='store_true', default=False,
                      help="unroll anchors/aliases (true *%default)")
    parser.add_option('-u', '--duplicate-keys', dest='duplicate_keys', action='store_true', default=False,
                      help="allow duplicate keys   (true *%default)")

    parser.add_option('-k', '--sort-keys', dest='sort_keys', action='store_true', default=False,
                      help="sort keys in dump      (true *%default)")
    parser.add_option('--sort-files', dest='sort_files', action='store_true', default=False,
                      help="sort input filenames   (true *%default)")
    parser.add_option('-r', '--reverse', dest='reverse', action='store_true', default=False,
                      help="sort direction         (true *%default)")

    parser.add_option('--suffix', dest='suffix', action='store', default='yaml')
    parser.add_option('-t', '--indent', dest='indent', action='store', type=int, default=2,
                      help="indent width           (%default)")
    parser.add_option('--loader', dest='loader', action='store', default='safe',
                      help="loader class           (base *%default roundtrip unsafe)")


    try:
        (options, args) = parser.parse_args()
    except Exception as e:
        parser.error(e)

    # mangle options.loader for API consuption
    options.loader= options.loader.lower()
    if options.loader == 'roundtrip':
        options.loader = 'rt'

    if isinstance(options.loglevel, str):
        options.loglevel = options.loglevel.upper()


    if options.logfile:
        log_handler = logging.FileHandler(options.logfile, mode='w')
    else:
        log_handler = logging.StreamHandler()
    log_handler.setFormatter(logging.Formatter('yamlreader: %(levelname)9s  %(message)s'))
    logger.addHandler(log_handler)
    logger.propagate = False
    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        # in 3.2+ we can do
        #logger.setLevel(options.loglevel)
        logger.setLevel(getattr(logging, options.loglevel, logging.INFO))

        # remove Traceback output in Verbose, squelch stacktrace all other times
        # if options.verbose:
            # sys.excepthook = lambda exctype,exc,traceback : print("{}: {}".format(exctype.__name__, exc))
        # else:
            # sys.excepthook = lambda *args: None

    # see http://yaml.readthedocs.io/en/latest/detail.html for examples
    data = new_data = None

    files = get_files(args, options.suffix)
    if len(files) == 0:
        #raise YamlReaderError('%s: "%s"' % (FileNotFoundError.__name__, str(args)), 'CRITICAL')
        raise YamlReaderError('No files found! %s' % str(args), logging.FATAL)
        # FATAL ==> not reached

    indent = {
        'mapping' : options.indent,
        'sequence': options.indent * 2,
        'offset'  : options.indent
        }

    myaml = yaml.YAML(typ=options.loader)
    myaml.preserve_quotes=True
    myaml.default_flow_style=False
    myaml.allow_duplicate_keys = options.duplicate_keys
    myaml.indent(mapping=indent['mapping'], sequence=indent['sequence'], offset=indent['offset'])
    myaml.representer.ignore_aliases = lambda *args: True

    # NOTICE! sort_keys is a noop unless using Matt's version of
    # Ruamel's YAML library (https://bitbucket.org/tb3088/yaml)
    if hasattr(myaml.representer, 'sort_keys'):
        myaml.representer.sort_keys = options.sort_keys

    for yaml_file in sorted(files, reverse=options.reverse) if options.sort_files else files:
        if options.verbose:
            logger.info('Reading file "%s"', yaml_file)
        try:
            new_data = myaml.load(open(yaml_file) if len(yaml_file) else sys.stdin)
            logger.debug('Payload: %r\n', new_data)
        except (yaml.MarkedYAMLError) as e:
            logger.warning('YAML.load() -- %s' % str(e))
            #raise YamlReaderError('YAML.load() -- %s' % str(e))

        if new_data: # is not None:
            data = data_merge(data, new_data, options.merge)
        else:
            logger.warning('No YAML data found in "%s"', yaml_file)

    if data is None or len(data) == 0:
        logger.critical('No YAML data found anywhere!')
        return 1

    try:
        if options.json:
            json.dump(data, sys.stdout, indent=indent['mapping'])
        else:
            myaml.dump(data, sys.stdout)
    except yaml.MarkedYAMLError as e:
        raise YamlReaderError('YAML.dump() -- %s' % str(e))
        #YamlReaderError("YAML.dump(): %s" % str(e))
    except (ValueError, OverflowError, TypeError):
        # JSON dump might trigger
        pass

        
if __name__ == "__main__":
    sys.exit(__main())
