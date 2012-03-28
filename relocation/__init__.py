from django.conf import settings

from relocation.engine import RelocationSerializer
from relocation.utils import buf_to_unicode, smart_import

def do_relocation(template_name, rendered_template):
    main, sections = RelocationSerializer.deserialize(rendered_template)
    for processor in settings.RELOCATION_PROCESSORS:
        ret = load_processor(processor)(template_name, main, sections)
        if ret is not None:
            main, sections = ret
    return buf_to_unicode(main)

def load_processor(processor_or_name):
    if callable(processor_or_name):
        return processor_or_name
    else:
        return smart_import(processor_or_name)

