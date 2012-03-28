import hashlib, logging
from bunch import Bunch

from django.conf import settings
from django.core.urlresolvers import reverse

from .cache import cached_data
from .utils import buf_to_unicode, smart_import

CACHE_NAME='relocations'
def relocation_cache_get_or_set(key_prefix, data, func):
    with cached_data('%s_%s' % (key_prefix, hashlib.md5(data).hexdigest()), backend=CACHE_NAME) as ctx:
        if not ctx.found:
            ctx.response = func(data)
    return ctx.response

def patch_cached_response(request, response):
    func_name = getattr(settings, 'RELOCATION_CACHED_RESPONSE_PATCH', None)
    if func_name:
        return smart_import(func_name)(request, response)

def external_http_reference(destination_format, reverse_view):
    return lambda template_name, section_name, section_data: (
        destination_format % reverse(reverse_view, args=(template_name, section_data)))

EXTERNIFY_VIEW = getattr(settings, 'RELOCATION_EXTERNIFY_VIEW', None)
EXTERNIFY_SECTION_RULES = Bunch(
    javascript = Bunch(
        reference = external_http_reference(
            destination_format = '<script type="text/javascript" src="%s"></script>',
            reverse_view = EXTERNIFY_VIEW,
        ),
        mimetype = 'application/javascript',
    ),
    css = Bunch(
        reference = external_http_reference(
            destination_format = '<link rel="stylesheet" type="text/css" href="%s"/>',
            reverse_view = EXTERNIFY_VIEW,
        ),
        mimetype = 'text/css',
    ),
)

def externify(template_name, main, sections, rules=EXTERNIFY_SECTION_RULES, prefix='externified_'):
    for section_name, ruledata in rules.items:
        if section_name not in sections:
            continue
        new_section_name = prefix+section_name
        sections[new_section_name] = sections[section_name].copy()
        sections[section_name].clear()
        sections[section_name].append(ruledata.reference(template_name, section_name, sections[new_section_name]))

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
