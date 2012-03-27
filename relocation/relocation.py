import hashlib, io
from bunch import Bunch
from collections import deque

from dtypes import mudeque

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

class RelocationError(Exception):
    pass

class RelocationSer(object):
    MAGICS = Bunch(
        RELOCATION_MAGIC = hashlib.sha1('dickus bigus').hexdigest(),
        TYPE_RELOCATE_START = 'RS',
        TYPE_RELOCATE_END = 'RE',
        TYPE_DESTINATION_MARKER = 'DM',
        NAME_START = '<',
        NAME_END = '>',
    )
    MAGIC_TYPE_LEN = 2
    MAX_NAME_LEN = 128

    @classmethod
    def relocate_start(cls, destination):
        return ''.join((
            cls.MAGICS.RELOCATION_MAGIC,
            cls.MAGICS.TYPE_RELOCATE_START,
            cls.MAGICS.NAME_START,
            destination,
            cls.MAGICS.NAME_END,
        ))

    @classmethod
    def relocate_end(cls):
        return ''.join((
            cls.MAGICS.RELOCATION_MAGIC,
            cls.MAGICS.TYPE_RELOCATE_END,
        ))

    @classmethod
    def destination(cls, destination):
        return ''.join((
            cls.MAGICS.RELOCATION_MAGIC,
            cls.MAGICS.TYPE_DESTINATION_MARKER,
            cls.MAGICS.NAME_START,
            destination,
            cls.MAGICS.NAME_END,
        ))

    @classmethod
    def deser(cls, s):
        """
        Takes a string with relocations markers and split it to into buffers
        returns: (main_buf, dict(section1=buf1, section2=buf2))

        All buffers are mudeques.
        The main_buf is contructed from the main part with the relocated buffers already injected in the right placeholders:

          u''.join(main_buf) -> Properly relocated string
          u''.join(section1) -> Only section1
          section1.clear()
          u''.join(main_buf) -> Relocated string with an empty section1

        """

        prev_index = 0
        buf_stack = deque((mudeque(),))
        current_buf = lambda: buf_stack[-1]
        relocations = dict()
        sss = SearchableStringStream(s)

        def getname():
            sss.expect(cls.MAGICS.NAME_START)
            name = sss.readuntil(cls.MAGICS.NAME_END)
            assert len(name) <= cls.MAX_NAME_LEN, "Got a too long name: %s"%(name)
            return name

        while True:
            try:
                current_buf().append(sss.readuntil(cls.MAGICS.RELOCATION_MAGIC))
            except EOFError:
                current_buf().append(sss.read())
                break

            magic_type = sss.read(cls.MAGIC_TYPE_LEN)
            if magic_type == cls.MAGICS.TYPE_RELOCATE_START:
                destination = getname()
                buf_stack.append(relocations.setdefault(destination, mudeque()))
            elif magic_type == cls.MAGICS.TYPE_RELOCATE_END:
                buf_stack.pop()
                assert len(buf_stack) > 0, "Encountered endrelocate without relocate"
            elif magic_type == cls.MAGICS.TYPE_DESTINATION_MARKER:
                destination = getname()
                current_buf().branch(relocations.setdefault(destination, mudeque()))
                current_buf().branch()
            else:
                raise RelocationError('Bad magic type: ' + magic_type)

        return buf_stack[0], relocations

    @classmethod
    def do_relocation(cls, s):
        main, relocations = cls.deser(s)
        return u''.join(main)
