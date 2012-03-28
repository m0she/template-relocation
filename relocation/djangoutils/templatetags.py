from django.template.base import Library, Node, TemplateSyntaxError, TextNode

from relocation.engine import RelocationSerializer
register = Library()

class NodeBasedNodeList(Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist
    def render(self, context):
        return self.nodelist.render(context)

@register.tag
def relocate(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'relocate' tag require a section name argument")
    dest = bits[1]

    nodelist = parser.parse(('endrelocate',))
    parser.delete_first_token()
    nodelist.insert(0, TextNode(RelocationSerializer.relocate_start(dest)))
    nodelist.append(TextNode(RelocationSerializer.relocate_end()))
    return NodeBasedNodeList(nodelist)

@register.tag
def destination(parser, token):
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError("'relocate' tag require a section name argument")
    dest = bits[1]
    return TextNode(RelocationSerializer.destination(dest))

