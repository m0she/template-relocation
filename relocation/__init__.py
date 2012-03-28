from django.conf import settings

from relocation.engine import RelocationSerializer
from relocation.utils import load_function

def perform_relocation(template_name, rendered_template):
    main, sections = RelocationSerializer.deserialize(rendered_template)
    for processor in settings.RELOCATION_PROCESSORS:
        load_function(processor)(template_name, main, sections)
    return main, sections
