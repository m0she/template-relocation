import os

DJANGO_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIRS = (os.path.join(DJANGO_PATH, 'templates'),)

RELOCATION_PROCESSORS = (
    'relocation.processors.scss',
    'relocation.processors.coffee',
    'relocation.processors.minify_js',
    'relocation.processors.externify',
)
RELOCATION_PROCESSORS = ()
