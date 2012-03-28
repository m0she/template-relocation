import io
from importlib import import_module

buf_to_unicode = lambda buf: u''.join(buf)

class SearchableStringStream(io.IOBase):
    def __init__(self, s=u''):
        self.s = s
        self.pos = 0
    def seek(self, pos, whence = 0):
        if whence == 0:
            new_pos = pos
        elif whence == 1:
            new_pos = self.pos + pos
        elif whence == 2:
            new_pos = len(self.s) + pos
        else:
            raise ValueError('Bad whence: %r'%whence)
        if new_pos < 0 or new_pos > len(self.s):
            raise ValueError('Bad position (was: %d, new: %d, pos: %d, whence: %d)'%(self.pos, new_pos, pos, whence))
        self.pos = new_pos

    def seekable(self):
        return True

    def readable(self):
        return True

    def read(self, size=-1):
        if size < 0:
            end = None
        else:
            end = self.pos + size
        ret = self.s[self.pos:end]
        self.pos += len(ret)
        return ret

    def find(self, sub, start=None, end=None):
        start = self.pos + (start or 0)
        if end is not None:
            end += self.pos
        return self.s.find(sub, start, end) - self.pos

    def readuntil(self, sub, start=None, end=None):
        count = self.find(sub, start, end)
        if count < 0:
            raise EOFError("Couldn't find '%s' in buffer (start=%r, end=%r)"%(sub, start, end))
        ret = self.read(count)
        self.seek(len(sub), 1)
        return ret

    def expect(self, expected):
        got = self.read(len(expected))
        assert got == expected, 'Expected: "%s". Got: "%s".'%(expected, got)


def smart_import(import_path):
    def resolve_part(base, part):
        if not base:
            return import_module(part)
        if hasattr(base, part):
            return getattr(base, part)
        return import_module('.'.join((base.__name__, part)))

    return reduce(lambda base,part: resolve_part(base, part), import_path.split('.'), None)

def load_function(function_or_name):
    if callable(function_or_name):
        return function_or_name
    else:
        return smart_import(function_or_name)

