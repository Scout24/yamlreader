from __future__ import print_function, absolute_import, unicode_literals, division

__version__ = '3.1.0'

import ruamel.yaml as yaml
from ruamel.yaml import MarkedYAMLError, safe_load, safe_dump
import glob
import os
import sys
import logging
import six

logger = logging.getLogger(__name__)


class YamlReaderError(Exception):
    def __init__(self, msg=''):
        super().__init__(msg)
        logger.error(msg, sys.exc_info())

    def __str__(str):
        return self.msg


def data_merge(a, b):
    """merges b into a and return merged result
    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays (append) and dict keys replaced if having the same name.

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen"""
    key = None

    logger.debug("data_merge(): %s to %s\n" %(b,a))
    try:
        if a is None or isinstance(a, (six.string_types, float, six.integer_types)):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = data_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                raise YamlReaderError('UNSUPPORTED merge non-dict "%s" into dict "%s"' % (b, a))
        else:
            raise YamlReaderError('NOT IMPLEMENTED "%s" into "%s"' % (b, a))
    except TypeError as e:
        raise YamlReaderError('TypeError "%s" in key "%s" when merging "%s" into "%s"' % (e, key, b, a))
    return a


def get_files(source, suffix='yaml'):
    """
    source can be a file, a directory, a list/tuple of files or
    a string containing a glob expression (with ?*[]).

    For a directory, filenames of *.yaml will be read.
    """
    files = []

    if type(source) is list or type(source) is tuple:
        # when called from __main() as get_files(args, ...), 'source' is always a list of size >=0.
        if len(source) == 1:
            # turn into a string to evaluate further
            source = source[0]
        else:
            for item in source:
                # iterate to expand list of potential dirs and files
                files.extend(get_files(item, suffix))
            return files

    if type(source) is not str or len(source) == 0 or source == '-':
        return []

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
