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
        elif new_auth_level > auth.current_user.auth_level:
            render.flash_error('You cannot promote someone to a role above your own.')
        elif user.auth_level > auth.current_user.auth_level:
            render.flash_error('You cannot change the user role for someone with a higher role than your own.')
        else:
            user.update_entry(user, user.id, auth_level=new_auth_level)
            render.flash_success('User role changed')
    return render.template('form.html', form=form, markdown=markdown_change_role())

############
### Text ###
############
def markdown_signup_link():
    signup_link = flask.url_for("user.signup", signup_key=database.Attrs.get("signup_key"), _external=True)
    return dict(before_content=f"""
    ### Signup link
    The signup link is: [{signup_link}]({signup_link})
    
    Users who sign up using this link will be automatically verified. The link is disabled when a new one is created.
    
    To create a new signup link click [here]({flask.url_for("admin.update_signup_link")}).
    """)

def markdown_change_role():
    return dict(
        before_form="""
        ### Change user role
        Select the user from the **User** field whose role you want to change. Their current role is displayed in front of their name.
        
        The available user roles are:
        
        - **Deactivated** - These users wont be allowed to login. To signify that, for whatever reason, this account has been banned or is no longer active.

        - **Unverified** - Can't upload data or do anything else. Safety precaution so if a random person that stumbles across the website can't start adding stuff to the database.
        
        - **Verified** - Can upload data and edit data that they have uploaded. They cannot edit data that other people have uploaded. If you use the signup link, you should become verified automatically (You weren’t; I've found and fixed that bug)
        
        - **Moderator** - Same as verified + they can edit all data, even that uploaded by other users. They cannot change user roles or update the signup link (But they can access it). For any person trusted not to mess things up.
        
        - **Administrator** - Same as a moderator + they can change user roles and update the signup link. Basically, this role is reserved for website/database administration and should be limited to only a select few.
        
        **Note** You cannot change the role of more powerful users or promote users to a role more powerful than your own.
        
        ---
        """
    )