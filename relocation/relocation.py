from bunch import Bunch
from collections import deque

from .utils import SearchableStringStream
from dtypes import mudeque

class RelocationError(Exception):
    pass

class RelocationSerializer(object):
    MAGICS = Bunch(
        RELOCATION_MAGIC = 'e50c9dec8d54890ad1b1405eb2229bd24d7f3f3f',
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
    def deserialize(cls, s):
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
        main, relocations = cls.deserialize(s)
        return u''.join(main)
