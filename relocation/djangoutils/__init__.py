from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.template.base import add_to_builtins, RequestContext

from ..utils import buf_to_unicode, load_function
from relocation import perform_relocation

def load_settings_function(settings_name, default_function=None):
    func = getattr(settings, settings_name, default_function)
    if not func:
        raise ImproperlyConfigured("Couldn't load function from settings: %s" % settings)
    return load_function(func)

def default_load_template(template_name):
    # don't invoke loader unless necessary
    from django.template.loader import get_template
    return get_template(template_name)

def default_get_context(request, template_name):
    return RequestContext(request)

get_context = load_settings_function('RELOCATION_GET_CONTEXT', default_get_context)
load_template = load_settings_function('RELOCATION_LOAD_TEMPLATE', default_load_template)
externified_response = load_settings_function('RELOCATION_EXTERNIFIED_RESPONSE', lambda template_name, section, data: HttpResponse(data))

def render_to_string(template_name, context):
    main, sections = perform_relocation(template_name, load_template(template_name).render(context))
    return buf_to_unicode(main)

def externified_view(request, template_name, section, data_hash=""):
    ## TODO: verify result with data_hash - less important since cache key is already effected by url
    main, sections = perform_relocation(template_name, load_template(template_name).render(get_context(request, template_name)))
    return externified_response(template_name, section, buf_to_unicode(sections[section]))

def relocation_add_to_builtins():
    add_to_builtins('relocation.djangoutils.templatetags')
