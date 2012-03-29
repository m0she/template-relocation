import copy, hashlib, logging
from bunch import Bunch

from django.conf import settings
from django.core.cache import DEFAULT_CACHE_ALIAS
from django.core.urlresolvers import reverse

from .cache import cached_data
from .utils import buf_to_unicode

CACHE_NAME=getattr(settings, 'RELOCATION_CACHE', DEFAULT_CACHE_ALIAS)
def relocation_cache_get_or_set(key_prefix, data, func):
    with cached_data('%s_%s' % (key_prefix, hashlib.md5(data).hexdigest()), backend=CACHE_NAME) as ctx:
        if not ctx.found:
            ctx.response = func(data)
    return ctx.response

def external_http_reference_with_data_hash(destination_format, reverse_view):
    def reference_builder(template_name, section_name, section_data):
        return destination_format % reverse(reverse_view, kwargs=dict(
            template_name=template_name,
            section=section_name,
            data_hash=hashlib.md5(buf_to_unicode(section_data)).hexdigest(),
        ))
    return reference_builder

def external_http_reference(destination_format, reverse_view):
    return lambda template_name, section_name, section_data: (
        destination_format % reverse(reverse_view, kwargs=dict(template_name=template_name, section=section_name)))

EXTERNIFY_VIEW = getattr(settings, 'RELOCATION_EXTERNIFY_VIEW', 'externified_view')
EXTERNIFY_SECTION_RULES = getattr(settings, 'RELOCATION_EXTERNIFY_RULES', None) or Bunch(
    javascript = Bunch(
        reference = external_http_reference_with_data_hash(
            destination_format = '<script type="text/javascript" src="%s"></script>',
            reverse_view = EXTERNIFY_VIEW,
        ),
        mimetype = 'application/javascript',
    ),
    css = Bunch(
        reference = external_http_reference_with_data_hash(
            destination_format = '<link rel="stylesheet" type="text/css" href="%s"/>',
            reverse_view = EXTERNIFY_VIEW,
        ),
        mimetype = 'text/css',
    ),
)

def externify(template_name, main, sections, rules=EXTERNIFY_SECTION_RULES):
    for section_name, ruledata in rules.items():
        if section_name not in sections:
            continue
        new_section = copy.deepcopy(sections[section_name])
        sections[section_name].clear()
        sections[section_name].append(ruledata.reference(template_name, section_name, new_section))
        sections[section_name] = new_section

scss_compiler = None
def get_scss_compiler():
    global scss_compiler
    if scss_compiler:
        return scss_compiler

    import scss
    # Use our own logger instead of their default
    scss.log = logging.getLogger('reloc.scss')
    scss_compiler = scss.Scss()
    return scss_compiler

def scss(template_name, main, sections):
    scss_sections = ('css',)
    for section in scss_sections:
        if section not in sections:
            continue
        scssed = relocation_cache_get_or_set('scss', buf_to_unicode(sections[section]), lambda data: get_scss_compiler().compile(data))
        sections[section].clear()
        sections[section].append(scssed)

def coffee(template_name, main, sections):
    from .coffeeutils import coffee as compile_coffeescript
    if not all(section in sections for section in ('coffee', 'javascript')):
        return

    sections['javascript'].append(buf_to_unicode(
        relocation_cache_get_or_set('coffee', part, compile_coffeescript) for part in sections['coffee']))

def minify_js(template_name, main, sections):
    import slimit
    section = 'javascript'
    if section not in sections:
        return
    minified = relocation_cache_get_or_set('minify', buf_to_unicode(sections[section]), slimit.minify)
    sections[section].clear()
    sections[section].append(minified)
