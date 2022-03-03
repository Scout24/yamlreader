# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

__all__ = ['getLevelName', 'getLevel'] #, 'getLevelOrName', '_checkLevel']

import logging

# private re-implementations till Python Core fixes Lib/logging
# XXX bug numbers here

def getLevelName(level, format='%s', no_match=None):
#            strict={'case': False, 'type': False, 'map': False},
#            fixup=False
    """Return the textual representation of 'level'.

    Whether predefined (eg. CRITICAL -> "CRITICAL") or user-defined via
    addLevelName(), the string associated with 'level' is chosen.
    Otherwise, 'level' (no_match == NONE) or 'no_match' is returned
    subject to formatting per 'format'.

    In the spirit of "be liberal in what you accept", any value of 'level'
    that survives int() will be accepted (FUTURE: subject to 'strict').

    Issue #29220 introduced the BAD IDEA that passing an empty string
    (an obvious TypeError) would return same. This was requested in order
    to squash the fall-thru behavior of returning "Level %s", when the
    multi-word response was itself the actual ERROR since it broke all
    field-based log processing! The astute reader will note that an empty
    string causes the same pathology...

    DEPRECATION WARNING:
      This function WRONGLY returned the mapped Integer if a String form
      was provided. This violates the clearly stated purpose and forces
      the caller into defensive Type checks or suffer future TypeErrors.

    NOTE:
      Does no bounds or validity checks. Use _checkLevel().

    FUTURE:
      In strict mode, enforce parameter dataType, case, or membership.
    """

    try:
        # check Name->Level in case called incorrectly (backward compat)
        if level in logging._nameToLevel:
            return format % level

        # retval = _checkLevel(level, flags, fix=T/F)
        # if isinstance(retval, bool) then handle pass/fail, else update level with fixed value

        result = logging._levelToName.get(int(level))
        if result is not None:
            return format % result

    except TypeError:
        if raiseExceptions:
            raise("parameter 'level' must reduce to an Integer")
    except ValueError:
        pass

    return format % level if no_match is None else format % no_match


def getLevel(levelName, no_match=logging.NOTSET):
#            strict={'case': False, 'type': False, 'map': False},
#            fixup=False
    """Return the numeric representation of levelName.

    see getLevelName() for background
    """
    try:
        result = logging._nameToLevel.get(levelName)
        if result is not None:
            return result

        return int(levelName)

    except ValueError:
        if raiseExceptions:
            raise("parameter 'levelName' must be a defined String")

    return no_match


def getLevelOrName(level):
    pass


def _checkLevel(level, case=False, type=False, map=False):
    #TODO define check as dictionary
    pass
    # """Check parameter against defined values
    #
    # Returns corresponding or original Integer, or NOTSET if no-match.
    # Will raise TypeError or ValueError as applicable.
    #
    # NOTE: Since all logging.$level() functions choose to emit based on
    # numeric comparison, a default of ERROR would be more logical.
    # """
    try:
        if isinstance(level, str):
            if not case:
                level = str.upper(level)
            rv = _nameToLevel.get(level)
            # if rv is None:
                # XXX what now?
        if isinstance(level, int) or not type:
            # flip negative values
            level = int(level)
            if level in _levelToName(level):
                rv = level
            else:
                # tolerate any Integer value
                rv = NOTSET if map else level
        if rv is None:
            level = str(level)
        if rv is None:
            if level in _levelToName or (not type and int(level) in _levelToName):
                rv = NOTSET if level < NOTSET else level
                # rv = level
        if rv is None and map:
            raise ValueError
        else:
            # return parameter even though invalid
            rv = level
            # sor level < NOTSET or level > ???:
            # #raise ValueError
            # if isinstance(level, int):
                # XXX check >NOTSET
            # else:
                # raise TypeError
        #FIXME - test harness injects '+1',  so tolerating
        # arbitrary integers is expected behavior. Why?
        #    raise ValueError
            rv = int(level)
    except (TypeError, ValueError, KeyError) as err:
        if raiseExceptions:
            # test harness (../test/test_logging) expects 'TypeError' ONLY
            raise TypeError("Level not an integer or a valid string: %r" % level) from err
    except Exception:
        pass

    return NOTSET - 1 if rv is None else rv
