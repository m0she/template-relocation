from django.template.base import RequestContext

def context_to_dict(context):
    ret = dict()
    for ctx in context:
        ret.update(ctx)
    return ret

def jinja_get_context(request, template_name):
    return context_to_dict(RequestContext(request))

