import keyword
import re
import tokenize

import six

isidentifier = str.isidentifier if six.PY3 else re.compile('^%s$' % tokenize.Name).match


def is_valid_identifier_for_namedtuple(name):
    return (
        not name.startswith('_') and  # _names are disallowed by namedtuple
        not keyword.iskeyword(name) and
        isidentifier(name))
