import flask
from flask import Blueprint
import secrets

import database, render, forms, auth

admin = Blueprint('admin', __name__)

#############
### Forms ###
#############

def change_level_form(user_choices):
    class Form(forms.FlaskForm):
        user = forms.IntSelectField('User', choices=user_choices, enumerate=False, validators=[forms.validators.DataRequired()])
        auth_role = forms.SelectField('Role', choices=[(auth.DEACTIVATED, 'Deactivated User'),
                                                (auth.UNVERIFIED, 'Unverified User'),
                                                (auth.VERIFIED, 'Verified User'),
                                                (auth.MODERATOR, 'Moderator'),
                                                (auth.ADMIN, 'Administrator')],
                               validators=[forms.validators.DataRequired()], coerce=int)
        button = forms.SubmitField('Change')
    return Form()


##############
### Routes ###
##############

@admin.route('/all_edits')
@auth.moderator_required
def all_edits():
    results = database.Edit.get_all(('User.name', 'datetime', 'table', 'item_id', 'column',
                                     'old_value', 'new_value'))
    headings = ('User Name', 'Timestamp', 'Table', 'Item Id', 'Column', 'Old Value', 'New Value')
    return render.table('table.html', headings, reversed(results))

@admin.route('/signup_link')
@auth.moderator_required
def signup_link():
    return render.template('base.html', markdown=markdown_signup_link())

@admin.route('/signup_link/update')
@auth.admin_required
def update_signup_link():
    database.Attrs.set('signup_key', secrets.token_urlsafe())
    render.flash_success('Signup key updated')
    return render.redirect('admin.signup_link')

@admin.route('/change_role', methods=['GET', 'POST'])
@auth.admin_required
def change_role():
    user_list = database.User.get_all()

    form = change_level_form([(user.id, f"{auth.role_description(user.auth_level)} | {user.name} | {user.email}") for user in user_list])

    if form.validate_on_submit():
        user = database.User.get_one(id=form.user.data, or_none=True)
        new_auth_level = form.auth_role.data
        if user is None:
            render.flash_error('User not found')
        elif user.auth_level > auth.ADMIN:
            render.flash_error('Cannot change user role for power admins')
        else:
            user.update_entry(user, user.id, auth_level=new_auth_level)
            render.flash_success('User role changed')
    return render.template('form.html', form=form)

############
### Text ###
############
def markdown_signup_link():
    return dict(before_content=f"""
    The signup link is: {flask.url_for("user.signup", signup_key=database.Attrs.get("signup_key"), _external=True)}
    
    To create a new signup link click [here]({flask.url_for("admin.update_signup_link")}).
    """)