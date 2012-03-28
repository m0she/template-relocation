import hashlib, logging
from bunch import Bunch

from django.conf import settings
from django.core.cache import cache as default_cache
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.template.context import RequestContext

from .cache import cached_data
from .djangoutils.utils import do_relocation
from .jinja import env, context_to_dict
from .engine import RelocationSerializer
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

class CachedExternalHtmlRelocation(object):
    def __init__(self, template, cache=None):
        self.template = template
        self.cache = cache or default_cache

    EMPTY_HASH = '18abebe'
    SECTION_RULES = Bunch(
        javascript = Bunch(
            destination_format = '<script type="text/javascript" src="%s"></script>',
            mimetype = 'application/javascript',
        ),
        css = Bunch(
            destination_format = '<link rel="stylesheet" type="text/css" href="%s"/>',
            mimetype = 'text/css',
        ),
    )

    def process(self, main, sections):
        for section in self.SECTION_RULES:
            if section in sections:
                cached_url = self.put_cache_data(section, buf_to_unicode(sections[section]))
                sections[section].clear()
                sections[section].append(self.SECTION_RULES[section].destination_format % cached_url)
        return main, sections

    def do_relocation(self, rendered_template):
        return buf_to_unicode(self.process(RelocationSerializer.deserialize(rendered_template))[0])

    def put_cache_data(self, section, data):
        data_hash = hashlib.md5(data).hexdigest()
        self.cache.set(self.get_key(section, data_hash), data)
        # Cache latest with no HASH
        self.cache.set(self.get_key(section, self.EMPTY_HASH), data)
        return reverse(self.get_cached_data, kwargs=dict(template_name=self.template, section=section, data_hash=data_hash))

    @classmethod
    def get_cached_data(cls, request, template_name, section, data_hash=EMPTY_HASH):
        self = cls(template_name)
        response_content = self.cache.get(self.get_key(section, data_hash))
        if response_content is None:
            self.render(context_to_dict(RequestContext(request)))
            response_content = self.cache.get(self.get_key(section, data_hash))
        response = HttpResponse(response_content, mimetype=self.SECTION_RULES[section].get('mimetype', None))
        patch_cached_response(request, response)

        return response

    def render(self, context):
        # TODO: Shouldn't be here, should it?
        return do_relocation(self.template, env.get_or_select_template(self.template).render(context))

    def get_key(self, section, data_hash):
        return 'external_relocation_cache.%s.%s.%s' % (self.template, section, data_hash)


def cached_external(template_name, main, sections, cache=None):
    instance = CachedExternalHtmlRelocation(template_name, cache)
    return instance.process(main, sections)

def setup_scss():
    import scss
    # Use our own logger instead of their default
    scss.log = logging.getLogger('reloc.scss')
    return scss.Scss()
scss_compiler = setup_scss()
def scss(template_name, main, sections):
    scss_sections = ('css',)
    for section in scss_sections:
        if section not in sections:
            continue
        scssed = relocation_cache_get_or_set('scss', buf_to_unicode(sections[section]), lambda data: scss_compiler.compile(data))
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
