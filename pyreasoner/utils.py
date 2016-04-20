import keyword
import re
import tokenize

import six

isidentifier = str.isidentifier if six.PY3 else re.compile('^%s$' % tokenize.Name).match


def is_valid_identifier(name):
    return not keyword.iskeyword(name) and isidentifier(name)
