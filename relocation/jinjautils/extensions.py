from jinja2 import nodes
from jinja2.ext import Extension

from ..engine import RelocationSerializer

def str_to_node(data, lineno=None):
    return nodes.Output([nodes.TemplateData(data, lineno=lineno)], lineno=lineno)

class RelocationExtension(Extension):
    tags = set(['relocate', 'destination'])

    def parse(self, parser):
        return getattr(self, next(parser.stream).value)(parser)

    def _get_destination(self, parser):
        destination = next(parser.stream).value
        return destination

    def relocate(self, parser):
        lineno = parser.stream.current.lineno
        destination = self._get_destination(parser)
        nodelist = parser.parse_statements(('name:endrelocate',), drop_needle=True)
        nodelist.insert(0, str_to_node(RelocationSerializer.relocate_start(destination), lineno=lineno))
        nodelist.append(str_to_node(RelocationSerializer.relocate_end(), lineno=lineno))
        return nodes.Scope(nodelist, lineno=lineno)

    def destination(self, parser):
        lineno = parser.stream.current.lineno
        destination = self._get_destination(parser)
        return str_to_node(RelocationSerializer.destination(destination), lineno=lineno)

