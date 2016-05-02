import keyword
import re
import tokenize

import six

isidentifier = re.compile('^%s$' % tokenize.Name).match if six.PY2 else str.isidentifier


def is_valid_identifier_for_namedtuple(name):
    return (
        not name.startswith('_') and  # _names are disallowed by namedtuple
        not keyword.iskeyword(name) and
        isidentifier(name))
