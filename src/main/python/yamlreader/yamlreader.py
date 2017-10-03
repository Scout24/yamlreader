#!env python3

from __future__ import print_function, absolute_import, unicode_literals, division

__version__ = '3.1.0'

import ruamel.yaml as yaml
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
            exc_info=(logger.getEffectiveLevel() == logging.DEBUG), kwargs)

        if (level == logging.FATAL):
            sys.exit(1)

        #TODO break out and differentiate as needed. some raise, others (all?) pass
        pass


def data_merge(a, b):
    """merges b into a and return merged result

    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays (append) and dict keys replaced if having the same name.

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen
    """
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
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    a[key] = data_merge(a[key], b[key]) if key in a else b[key]
            else:
                raise TypeError
        else:
            raise TypeError

#----- original
        # if a is None or isinstance(a, (six.string_types, float, six.integer_types)):
            # # border case for first run or if a is a primitive
            # a = b
        # elif isinstance(a, list):
            # # lists can be only appended
            # if isinstance(b, list):
                # # merge lists
                # a.extend(b)
            # else:
                # # append to list
                # a.append(b)
        # elif isinstance(a, dict):
            # # dicts must be merged
            # if isinstance(b, dict):
                # for key in b:
                    # if key in a:
                        # a[key] = data_merge(a[key], b[key])
                    # else:
                        # a[key] = b[key]
            # else:
                # raise YamlReaderError('Illegal - %s into %s\n  "%s" -> "%s"' %
                    # (type(b), type(a), b, a), logging.WARNING)
        # else:
            # raise YamlReaderError('TODO - %s into %s\n  "%s" -> "%s"' %
                # (type(b), type(a), b, a), logging.WARNING)
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

    return files


def __main():
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] source ...",
                                   description="Merge YAML data from given files, directory or glob",
                                   version="%" + "prog %s" % __version__,
                                   prog='yamlreader')

    parser.add_option('-d', '--debug', dest='debug', action='store_true', default=False,
                      help="Enable debug logging [%default]")
    parser.add_option('-t', '--indent', dest='indent', action='store', type='int', default=2,
                      help="indent width [%default ]")
    parser.add_option('--loader', dest='loader', action='store', default='safe',
                      help="loader class [ %default ]")
    parser.add_option('--dumper', dest='dumper', action='store', default='safe',
                      help="dumper class [ %default ]")
    # CloudFormation can't handle anchors
    parser.add_option('-x', '--no-anchor', dest='no_anchor', action='store_true', default=False,
                      help="unroll anchors and aliases [ %default ]")
    parser.add_option('--sort-files', dest='sort_files', action='store_true', default=False,
                      help="sort input filenames [ %default ]")
    parser.add_option('-r', '--reverse', dest='reverse', action='store_true', default=False,
                      help="sort direction [ %default ]")
    parser.add_option('-k', '--sort-keys', dest='sort_keys', action='store_true', default=False,
                      help="sort keys in dump [ %default ]")
    parser.add_option('-l', '--logfile', dest='logfile', action='store', default=None)
    parser.add_option('--suffix', dest='suffix', action='store', default='yaml')

    try:
        (options, args) = parser.parse_args()
    except Exception as e:
        parser.error(e)

    log_handler = logging.StreamHandler(options.logfile)
    log_handler.setFormatter(logging.Formatter('yamlreader: %(levelname)s: %(message)s'))
    logger.addHandler(log_handler)
    if options.debug:
        logger.setLevel(logging.DEBUG)

    # see http://yaml.readthedocs.io/en/latest/detail.html for examples
    indent = {'mapping': options.indent, 'sequence': options.indent * 2, 'offset': options.indent}
    data = None
    files = get_files(args, options.suffix)

    myaml = yaml.YAML(typ='safe')
    myaml.preserve_quotes=True
    myaml.default_flow_style=False
    myaml.indent(mapping=indent['mapping'], sequence=indent['sequence'], offset=indent['offset'])
    myaml.representer.ignore_aliases = lambda *args: True
    # NOTICE! sort_keys *ONLY* works with matt's version
    myaml.representer.sort_keys = options.sort_keys

    if len(files) == 0:
        # Hack! force at least 1 pass thru FOR loop and '' stands in for <STDIN>
        files = ['']

    for yaml_file in sorted(files, reverse=options.reverse) if options.sort_files else files:
        logger.debug("Reading file %s\n", yaml_file)
        try:
            #new_data = yaml.load(open(yaml_file) if len(yaml_file) else sys.stdin, Loader=Loader, preserve_quotes=True)
            new_data = myaml.load(open(yaml_file) if len(yaml_file) else sys.stdin)
            logger.debug("YAML Load: %s", new_data)
        except MarkedYAMLError as e:
            # logger.exception("YAML Error: %s", e)
            raise YamlReaderError("YAML Error: %s" % str(e))

        if new_data is not None:
            data = data_merge(data, new_data)

    if not len(data):
        logger.warn("No YAML data found in %s", source)
    else:
        try:
            myaml.dump(data, sys.stdout)
        except Exception as e:
            logger.exception(e, sys.exc_info())

        
if __name__ == "__main__":
    __main()
