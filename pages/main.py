from flask import Blueprint

import forms, database, render

main = Blueprint('main', __name__)

#############
### Forms ###
#############

class SearchForm(forms.FlaskForm):
    sample_type = forms.SelectMultipleField('Sample Type:')
    element = forms.SelectMultipleField('Element:')
    search = forms.SubmitField('Search')

##############
### Routes ###
##############

@main.route('/', methods=['GET', 'POST'])
@main.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    form.sample_type.choices = sorted(database.Data.get_all('sample_type', distinct=True))
    form.element.choices = sorted(database.Data.get_all('element', distinct=True))

    if form.validate_on_submit():
        headings, results = database.Data.get_search(sample_type=form.sample_type.data,
                                           element=form.element.data)
    else:
        headings, results = database.Data.get_search(headings_only=True)

    return render.table('form_table.html', headings, results, result_types = {"Link": 'html'},
                        form=form, markdown=search_markdown())
############
### Text ###
############

def search_markdown():
    return dict(
        before_table="""
        ### Search Results
        """,
        before_form = """
        ### Welcome to the ChETEC-INFRA Stable Isotope Database
        
        Select your sample type and element of interest from the form below and the papers
        containing this type of data will be displayed.
        """)
