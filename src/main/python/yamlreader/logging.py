# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

__all__ = ['getLevelName', 'getLevel'] #, 'getLevelOrName', '_checkLevel']

import logging

# private re-implementations till Python Core fixes Lib/logging
# XXX bug numbers here

# define missing syslog(3) levels and also handy helpers
logging.addLevelName(logging.NOTSET, 'ALL')
logging.addLevelName(logging.DEBUG - 5, 'TRACE')
logging.addLevelName(logging.INFO + 5, 'NOTICE')
# fix Lib/logging improperly conflating CRITICAL and FATAL
logging.addLevelName(logging.CRITICAL + 1, 'FATAL')
logging.addLevelName(logging.CRITICAL + 10, 'ALERT')
logging.addLevelName(logging.CRITICAL + 20, 'EMERG')
logging.addLevelName(logging.CRITICAL + 99, 'ABORT')


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
        if level in _nameToLevel:
            return format % level

        # retval = _checkLevel(level, flags, fix=T/F)
        # if isinstance(retval, bool) then handle pass/fail, else update level with fixed value

        result = _levelToName.get(int(level))
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
        result = _nameToLevel.get(levelName)
        if result is not None:
            return result

        return int(levelName)

    except ValueError:
        if raiseExceptions:
            raise("parameter 'levelName' must be a defined String")
        
    return no_match


def getLevelOrName(level):
    pass


def _checkLevel(level):
    pass
# #            strict={'case': False, 'type': False, 'map': False},

    # """Check parameter against defined values. 
    # ???Return NOTSET if invalid.

    # Since all logging.$level() functions choose to emit based on
    # numeric comparison, a default of ERROR would be more friendly.
    # """
    # rv = NOTSET
    # try:
        # if level in _nameToLevel:
            # rv = _nameToLevel[level]
        # elif level in _levelToName:
            # rv = level
        # else:
        # #FIXME - test harness injects '+1',  so tolerating 
        # # arbitrary integers is expected behavior. Why?
        # #    raise ValueError
            # rv = int(level)
    # except (TypeError, ValueError, KeyError) as err:
        # if raiseExceptions:
            # # test harness (../test/test_logging) expects 'TypeError'
            # raise TypeError("Level not an integer or a valid string: %r" % level) from err
    # except Exception:
        # pass

      # return rv	

      


