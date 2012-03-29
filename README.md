# Relocation
Relocation package provides a way to post process a specific parts a rendered template.
It's primary usage is to enable web developers to author webpages of the different
languages/formats (HTML DOM, CSS and Javascript) while encapsulating the logic of single
web components into one single code file.

The processors will later *dynamically* extract the different parts, parse/compile/minify
the data and finally will cache and serve the extracted data sections while leaving HTML links 
pointing to it inside the original html document!

A typical component page might would look similarly to this:

    <div class="deck">
        <div class="card">{{ deck.first_card }}</div>
    </div>
    {% relocate css %}
        .deck .card { color: #f00; }
    {% endrelocate %}
    {% relocate coffeescript %}
        $('.card').click = (event) -> console.log "Card was clicked: ", $(@).html()
    {% endrelocate %}


The implementation is almost completely orthogonal to the templating language used and utilities
are currently provided for django builtin templating language and for jinja2.

Included also are the necessary code and configurations needed to setup end-to-end solution
for integration with any django based project. (settings, urls, views, `render_to_string`, etc..)

## Basic configuration

The following settings are used by different parts of the relocation package
### settings.py

* `RELOCATION_PROCESSORS` - The ordered list of processors

        RELOCATION_PROCESSORS = (
            'relocation.processors.scss',
            'relocation.processors.coffee',
            'relocation.processors.minify_js',
            'relocation.processors.externify',
        )

* `RELOCATION_LOAD_TEMPLATE` - A function that loads and returns a template 
    (set in order to use a different templating system other than django)
* `RELOCATION_CACHE` - Cache backend to use for caching processors' 
* Externify settings
    * `RELOCATION_EXTERNIFY_VIEW` - The name/import path of the view to the externified sections created
    by the externify processor.
    * `RELOCATION_GET_CONTEXT` - A function that returns a default context variable base on the request
        object and template_name. (Used for 
    * `RELOCATION_EXTERNIFIED_RESPONSE` - A function that returns a Response object from the extracted data


## Processors
* `scss` - Compiles scss code into css. Currently operates only on 'css' section. Requires pyScss package
* `coffee` - Compiles coffeescript from section 'coffee' into 'javascript'. Uses included pejis+coffee package.
    A supported javascript engine in needed (V8, nodejs, etc)
* `minify_js` - Minifies javascript within the 'javascript' section.

### externify
Extracts one or more sections from the main document and leave a link for external access to the data.
To use you'll need to add something along the following lines to urls.py (see [Caching](#caching) below):

    from django.conf.urls.defaults import include, patterns, url
    from django.views.decorators.cache import cache_page
    from relocation.djangoutils import externified_view

    urlpatterns = patterns('',
        url(r'^relocation/(?P<section>[^/]+)/(?P<template_name>.*)/(?P<data_hash>.*)$',
            cache_page(externified_view, 30*24*60*60), name='externified_view'),
    )

## Caching <div id="caching"></div>
The templates processing can be quite heavy. The relocation package contains built-in cache support in each processor.
Additionally, the externally served sections should be static per template (it's recommended, but up to you)
and then can be cached by django, external cache and/or a smart CDN.
A more framework level caching of the processors is planned in the future (once a mudeque document is pickle-able)

## Django templating system
In order to use the `relocate` and `destination` templatetags you should add the following code
to your startup/settings code:

### wsgi.py:

    from relocation.djangoutils import relocation_add_to_builtins
    relocation_add_to_builtins()

You would also want to use `relocation.djangoutils.render_to_string` which

## Jinja2
* TODO - write about jinja support


## Requirements

    pip install django bunch

### Optional packages

    pip install pyScss slimit Jinja2


## Credits
* The use case concept for the relocation was conceived by *Avner Braverman* along with a fully functional django specific implementation
* Pejis (from coffeeutils) is heavily based on PyExecJS and was adopted into pejis by *Yaniv Aknin*
* Some of the ideas/code is based on/copied from work done by *Audish development team*
* Permission to distribute under attached `LICENSE.txt` was granted by all relevant parties

