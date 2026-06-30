import re
from .get_config import GetConfig

_cf = GetConfig()


class Context:
    memberid = _cf.get_value("data", "memberid")
    pwd = _cf.get_value("data", "pass")


def replace_variable(s, data):
    p = r"\$\{(.*?)\}"
    while re.search(p, s):
        g = re.search(p, s)
        key = g.group(1)
        value = data[key]
        s = re.sub(p, value, s, count=1)
    return s


def replace_variable_new(s):
    p = r"\$\{(.*?)\}"
    while re.search(p, s):
        g = re.search(p, s)
        key = g.group(1)
        if hasattr(Context, key):
            value = getattr(Context, key)
            s = re.sub(p, value, s, count=1)
        else:
            return None
    return s
