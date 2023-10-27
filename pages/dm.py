import re

from flask import Blueprint

import render, forms, auth, database

dm = Blueprint('dm', __name__)

#############
### Forms ###
#############
class EditDataFrom(forms.FlaskForm):
    id = forms.SelectField('Data Id:', validators=[forms.validators.InputRequired()], coerce=int)
    sample_type = forms.StringField('Sample Type:', validators=[forms.validators.Length(0, 150)])
    element = forms.StringField('Element:', validators=[forms.validators.InputRequired(), forms.validators.Length(1, 2)])


def add_citation_form(button_text = 'Submit',
                      allowed_doi = '', **defaults):
    def doi_validator(form, field):
        doi = field.data
        if m := re.search(".*(10[.][\d.]*[/].*)$", doi):
            doi = m.group(1)
            if doi in database.Citation.get_all('doi') and doi != allowed_doi:
                raise forms.ValidationError('A citation with this DOI already exits')
        else:
            raise forms.ValidationError('Invalid DOI')

    def ads_validator(form, field):
        ads = field.data
        if ads != '' and not ads.startswith('https://ui.adsabs.harvard.edu/'):
            raise forms.ValidationError('Invalid ADS')

    journal_list = ["<New Journal>"] + database.Citation.get_all('journal', distinct=True)

    class Form(forms.FlaskForm):
        authors = forms.StringField('Authors:', default=defaults.get('authors', None), validators=[forms.validators.Length(1, 150)])
        year = forms.IntegerField('Year:', default=defaults.get('year', 2023), validators=[forms.validators.NumberRange(1850, 2050)])
        journal = forms.NewEntrySelectField('Journal:', 'journal_new', journal_list, default=defaults.get('journal', 0), validators=[forms.validators.InputRequired()])
        journal_new = forms.StringField('New Journal:', validators=[forms.validators.Length(0, 150)])
        doi = forms.StringField('DOI:', default=defaults.get('doi', None), validators=[forms.validators.InputRequired(), forms.validators.Length(1, 150), doi_validator])
        ads = forms.StringField('ADS:', default=defaults.get('ads', None), validators=[forms.validators.Length(0, 150), ads_validator])
        button = forms.SubmitField(button_text)

    return Form()

def add_data_form(citation_id = None,
                  button_text = 'Submit',
                  multi_element = False,
                  **defaults):
    if citation_id:
        citation_choices = database.Citation.get_citations(sort=True, id=citation_id)
    else:
        citation_choices = database.Citation.get_citations(sort=True)

    if len(citation_choices) == 0:
        render.flash_error('Invalid citation id')

    sample_type_choices = ['<New Sample Type>'] + database.Data.get_all('sample_type', distinct=True)

    def element_validator(form, field):
        if multi_element:
            elements = [e.strip().capitalize() for e in field.data.split(',')]
            for element in elements:
                if len(element) > 2 or len(element) < 1:
                    raise forms.ValidationError(f'Invalid element symbol ("{element}")')
        else:
            element = field.data
            if len(element) > 2 or len(element) < 1:
                raise forms.ValidationError(f'Invalid element symbol ("{element}")')

    class Form(forms.FlaskForm):
        citation = forms.IntSelectField('Citation:',
                                  choices = citation_choices,
                                  default=defaults.get('citation', None),
                                  enumerate=False,
                                  validators=[forms.validators.InputRequired()])
        sample_type = forms.NewEntrySelectField('Sample Type:', 'sample_type_new', sample_type_choices,
                                               default=defaults.get('sample_type', None),
                                               validators=[forms.validators.InputRequired()])
        sample_type_new = forms.StringField('New Sample Type:',
                                             validators=[forms.validators.Length(0, 150)])
        element = forms.StringField('Element:',
                                  default=defaults.get('element', None),
                                  validators=[forms.validators.InputRequired(), element_validator])
        button = forms.SubmitField(button_text)

    return Form()


#############
### Pages ###
#############

@dm.route('/add_citation', methods=['GET', 'POST'])
@auth.verified_required
def add_citation():
    # Forwards to add_data with doi when submitted
    # redirect(url_for('add_data', doi=doi))
    form = add_citation_form()

    if form.validate_on_submit():
        try:
            new_citation = database.Citation.new_entry(auth.current_user,
                                                          creator_id = auth.current_user.id,
                                                          authors = form.authors.data,
                                                          year = form.year.data,
                                                          journal=form.journal.choice,
                                                          doi = form.doi.data,
                                                          ads = form.ads.data)
        except Exception as err:
            render.flash_error(str(err))
        else:
            render.flash_success('Citation added')
            return render.redirect('dm.add_data', citation_id=new_citation.id)

    return render.template('form.html', form=form, markdown=add_citation_markdown())


@dm.route('/add_data', methods=['GET', 'POST'])
@dm.route('/add_data/<int:citation_id>', methods=['GET', 'POST'])
@auth.verified_required
def add_data(citation_id = None):
    form = add_data_form(citation_id = citation_id, multi_element=True)
    if form.validate_on_submit():
        try:
            elements = [e.strip().capitalize() for e in form.element.data.split(',')]
            for element in elements:
                new_data = database.Data.new_entry(auth.current_user,
                                                  creator_id=auth.current_user.id,
                                                  citation_id=form.citation.data,
                                                  sample_type=form.sample_type.choice,
                                                  element=element)
        except Exception as err:
            render.flash_error(str(err))
        else:
            render.flash_success('Data added')
            form = add_data_form(citation_id = citation_id, sample_type=form.sample_type.data)

    return render.template('form.html', form=form, markdown=add_data_markdown())


@dm.route('/edit', methods=['GET', 'POST'])
@auth.verified_required
def edit():
    def data_id_validator(form, field):
        if form.table_.data == 'Citation' and database.Citation.get_one(id=field.data, or_none=True) is not None:
            return

        if form.table_.data == 'Data' and database.Data.get_one(id=field.data, or_none=True) is not None:
            return

        raise forms.ValidationError('Invalid id')

    class Form(forms.FlaskForm):
        table_ = forms.SelectField('Table', choices = ['Citation', 'Data'], validators=[forms.validators.InputRequired()])
        id = forms.IntegerField('Id:', validators=[forms.validators.InputRequired(), data_id_validator])
        button = forms.SubmitField('Edit')

    form = Form()

    if form.validate_on_submit():
        if form.table_.data == 'Citation':
            item = database.Citation.get_one(id = form.id.data, or_none = True)
            address = 'dm.edit_citation'
        else:
            item = database.Data.get_one(id = form.id.data, or_none = True)
            address = 'dm.edit_data'

        if item is None:
            render.flash_error('This Id does not exist')
        elif auth.current_user.auth_level < auth.MODERATOR and item.creator_id != auth.current_user.id:
            render.flash_error('You are not authorised to edit data created by someone else')
        else:
            return render.redirect(address, id = item.id)

    citations = dict(database.Citation.get_citations())
    headings = ('Citation Id', 'Citation', 'Data Id', 'Sample Type', 'Element')
    results = [(row.citation_id, citations[row.citation_id], row.id, row.sample_type, row.element)
               for row in database.Data.get_all()]

    return render.table('form_table.html', headings, results, search=True,
                        form=form)

@dm.route('/edit_citation/<int:id>', methods=['GET', 'POST'])
@auth.verified_required
def edit_citation(id):
    citation = database.Citation.get_one(id=id, or_none=True)
    if citation is None:
        render.flash_error('Invalid citation id')
        render.redirect('dm.edit')

    if auth.current_user.auth_level < auth.MODERATOR and citation.creator_id != auth.current_user.id:
        render.flash_error('You are not authorised to edit data created by someone else')
        render.redirect('dm.edit')

    form = add_citation_form(button_text='Edit', allowed_doi=citation.doi,
                             authors=citation.authors,
                             year=citation.year,
                             journal=citation.journal,
                             doi=citation.doi,
                             ads=citation.ads
                             )

    if form.validate_on_submit():
        edited = database.Citation.update_entry(auth.current_user, citation.id,
                                                authors=form.authors.data,
                                                year=form.year.data,
                                                journal=form.journal.choice,
                                                doi=form.doi.data,
                                                ads=form.ads.data)
        if edited:
            render.flash_success('Entry was updated')
        else:
            render.flash_message('No changes were made to the entry')

    results = database.Edit.get_all(('User.name', 'datetime', 'table', 'item_id', 'column',
                                     'old_value', 'new_value'), item_id=citation.id, table='Citation')
    headings = ('User Name', 'Timestamp', 'Table', 'Item Id', 'Column', 'Old Value', 'New Value')

    return render.table('form_table.html', headings, reversed(results), form=form)

@dm.route('/edit_data/<int:id>', methods=['GET', 'POST'])
@auth.verified_required
def edit_data(id):
    data = database.Data.get_one(id=id, or_none=True)
    if data is None:
        render.flash_error('Invalid data id')
        render.redirect('dm.edit')

    if auth.current_user.auth_level < auth.MODERATOR and data.creator_id != auth.current_user.id:
        render.flash_error('You are not authorised to edit data created by someone else')
        render.redirect('dm.edit')

    form = add_data_form(citation_id = data.citation_id,
                         sample_type=data.sample_type,
                         element=data.element,
                         button_text='Edit')

    if form.validate_on_submit():
        edited = database.Data.update_entry(auth.current_user, data.id, sample_type = form.sample_type.choice, element=form.element.data)
        if edited:
            render.flash_success('Entry was updated')
        else:
            render.flash_message('No changes were made to the entry')

    results = database.Edit.get_all(('User.name', 'datetime', 'table', 'item_id', 'column',
                                     'old_value', 'new_value'), item_id=data.id, table='Data')
    headings = ('User Name', 'Timestamp', 'Table', 'Item Id', 'Column', 'Old Value', 'New Value')

    return render.table('form_table.html', headings, reversed(results), form=form)

def add_citation_markdown():
    return dict(
        before_form = """
        ### Add Citation
        This is the form for adding a citation to the database. Once submitted you will be taken to the form
        to add data associated with this citation.
        
        - **Authors**: Please give author names as "First, N.; Second, N." etc. Use ";" to separate authors in the list.
        - **Year**: Year of publication.
        - **Journal**: If the Journal is not listed here, select "&lt;New&nbsp;Journal&gt;" and type the journal name in the
        **New&nbsp;Journal** field.
        - **DOI**: The Digital Object Identifier. This should be listed on the articles journal website.
        - **ADS**: The link to the article entry on the [Astrophysics Data System](https://ui.adsabs.harvard.edu).
        """
    )


def add_data_markdown():
    return dict(
        before_form="""
        ### Add Data
        This is the form for adding a stable isotope data associated with a given citation to the database.

        - **Citation**: Select the citation this data is associated with.
        - **Sample Type**: The sample type that was analysed for the given element(s). If the sample typ[e is not 
        listed here, select "&lt;New&nbsp;Sample&nbsp;Type&gt;" and type the 
        sample type in the **New&nbsp;Sample&nbsp;Type** field.
        - **Element**: The element symbol. Multiple elements can be added by separating them with ", ".
        """
    )