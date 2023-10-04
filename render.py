import flask
from flask import url_for
from inspect import cleandoc
from markdown import markdown as mkd

__all__ = ['flash_message', 'flash_error', 'flash_success',
           'template', 'redirect', 'table', 'url_for']

_app = None

def init(app):
    globals()['_app'] = app

def flash_message(message):
    flask.flash(message)

def flash_error(message):
    flask.flash(message, 'error')

def flash_success(message):
    flask.flash(message, 'success')

def redirect(funcname, **kwargs):
    return flask.redirect(flask.url_for(funcname, **kwargs))

def table(template, headings, results, result_types = None,
                 search=False, pagination=True, **kwargs):
    heading_ids = [heading.replace(' ', '_') for heading in headings]
    columns = ''.join([f"{{ id: '{hid}', name: '{heading}' }}, \n" for hid, heading in zip(heading_ids, headings)])

    if result_types is None:
        result_types = {}
    elif isinstance(result_types, (tuple, list)):
        if len(result_types) != len(headings):
            raise ValueError('Length of result_types does not match the  number of headings.')
        else:
            result_types = dict(zip(headings, result_types))
    elif type(result_types) is not dict:
        result_types = {h: result_types for h in headings}

    data = []
    for row in results:
        row_data = ''
        for i, column in enumerate(row):
            result_type = result_types.get(headings[i], None)
            if result_type == 'html':
                column = f"gridjs.html('{column}')"
            elif result_type == 'number' or (result_type is None and isinstance(column, (int, float))):
                column = f"{column}"
            else:
               column = f"'{column}'"
            row_data += f"{heading_ids[i]}: {column},\n"
        data.append(f"{{\n{row_data}}}, \n")
    data = ''.join(data)

    if search:
        search = 'true'
    else:
        search = 'false'

    if pagination is True:
        pagination = '{ limit: 30, summary: false }'
    elif type(pagination) is int:
        pagination = f'{{ limit: {pagination}, summary: false }}'
    else:
        pagination = 'false'

    return render_template(template,
                           table_columns = columns,
                           table_data = data,
                           table_search = search,
                           table_pagination = pagination,
                           **kwargs)
    """
        columns: [ { id: 'authors', name: 'Authors' },
                       { id: 'year', name: 'Year' },
                       { id: 'journal', name: 'Journal' },
                       { id: 'sampletype', name: 'Sample Type' },
                       { id: 'element', name: 'Element' },
                       { id: 'link', name: 'Links' },
            ],
            data: [
                {% for result in table_results %}
                    {
                        authors: '{{ result["authors"] }}',
                        year: '{{ result["year"] }}',
                        journal: '{{ result["journal"]|safe}}',
                        sampletype: '{{ result["sampletype"] }}',
                        element: '{{ result["element"] }}',
                        link: gridjs.html('{{ result["link"]|safe }}'),
                    },
                {%  endfor %}
            ],
            """

def template(template, *args, markdown = None, **kwargs):
    if markdown and type(markdown) is not dict:
        raise TypeError('markdown must be a dict')
    elif markdown:
        kwargs.update({k: mkd(cleandoc(v)) for k,v in markdown.items()})

    return flask.render_template(template, *args, **kwargs)

render_template = template