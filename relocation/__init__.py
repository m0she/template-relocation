from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse

from relocation.engine import RelocationSerializer
from relocation.utils import buf_to_unicode, smart_import

def do_relocation(template_name, rendered_template):
    main, sections = RelocationSerializer.deserialize(rendered_template)
    for processor in settings.RELOCATION_PROCESSORS:
        load_function(processor)(template_name, main, sections)
    return main, sections

def load_function(function_or_name):
    if callable(function_or_name):
        return function_or_name
    else:
        return smart_import(function_or_name)

def load_settings_function(settings_name, default_function=None):
    func = getattr(settings, settings_name, default_function)
    if not func:
        raise ImproperlyConfigured("Couldn't load function from settings: %s" % settings)
    return load_function(func)

def default_load_template(template_name):
    from django.template.loader import get_template
    return get_template(template_name)

def default_get_context(request, template_name):
    from django.template import RequestContext
    return RequestContext(request)

get_context = load_settings_function('RELOCATION_GET_CONTEXT', default_get_context)
load_template = load_settings_function('RELOCATION_LOAD_TEMPLATE', default_load_template)
externified_response = load_settings_function('RELOCATION_EXTERNIFIED_RESPONSE', lambda template_name, section, data: HttpResponse(data))

def render_to_string(template_name, context):
    main, sections = do_relocation(template_name, load_template(template_name).render(context))
    return buf_to_unicode(main)

def externified_view(request, template_name, section):
    main, sections = do_relocation(template_name, load_template(template_name).render(get_context(request, template_name)))
    return externified_response(template_name, section, sections[section])

