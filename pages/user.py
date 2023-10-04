from functools import wraps

import flask
from flask import Blueprint
from flask_login import login_user, logout_user, current_user


import forms, database, render, auth

user = Blueprint('user', __name__)

#############
### Forms ###
#############

class LoginForm(forms.FlaskForm):
    email = forms.StringField('Email:', validators=[forms.validators.DataRequired(), forms.validators.Email()])
    password = forms.PasswordField('Password:', validators=[forms.validators.DataRequired()])
    button = forms.SubmitField('Login')

class SignupForm(forms.FlaskForm):
    name = forms.StringField('Name:', validators=[forms.validators.DataRequired(), forms.validators.Length(1, 150)])
    email = forms.StringField('Email:', validators=[forms.validators.DataRequired(), forms.validators.Email()])
    password = forms.PasswordField('Password:', validators=[forms.validators.DataRequired(), forms.validators.EqualTo('password2','Passwords do not match')])
    password2 = forms.PasswordField('Re-enter Password:', validators=[forms.validators.DataRequired()])
    recaptcha = forms.RecaptchaField()
    button = forms.SubmitField('Sign up')

class ChangePasswordForm(forms.FlaskForm):
    old_password = forms.PasswordField('Password:', validators=[forms.validators.DataRequired()])
    new_password = forms.PasswordField('Password:', validators=[forms.validators.DataRequired(),
                                                            forms.validators.EqualTo('new_password2', 'Passwords do not match')])
    new_password2 = forms.PasswordField('Re-enter Password:', validators=[forms.validators.DataRequired()])
    button = forms.SubmitField('Change password')

##############
### Routes ###
##############

@user.route('/login', methods=['GET', 'POST'])
def login():
    if auth.current_user.is_active:
        render.flash_error('You are already signed in')
        return render.redirect('main.search')

    form = LoginForm()
    if form.validate_on_submit():
        user = database.User.get_one(email=form.email.data, or_none=True)
        if user:
            if database.User.verify_password(user.id, form.password.data):
                login_user(user)
                render.flash_success(f'Welcome {user.name}')
                return render.redirect('main.search')
            else:
                render.flash_error('Invalid password')
                return render.template('form.html', form=form)
        else:
            render.flash_error('No account exists with this email')
            return render.template('form.html', form=form)
    else:
        return render.template('form.html', form=form, markdown=login_text())

@user.route('/logout')
@auth.required(auth.DEACTIVATED)
def logout():
    logout_user()
    render.flash_success("You have been logged out")
    return render.redirect('main.search')

@user.route('/signup', methods=['GET', 'POST'])
def signup():
    if auth.current_user.is_active:
        render.flash_error('Sign out to create a new account')
        return render.redirect('main.search')

    signup_key = flask.request.args.get('signup_key')
    if signup_key is None:
        render.flash_error('Sign ups are invite only. Contact an administrator to sign up.')
        return render.redirect('user.login')
    elif signup_key != database.Attrs.get('signup_key'):
        render.flash_error('Invalid signup link. Contact an administrator.')
        return render.redirect('user.login')

    form = SignupForm()
    if form.validate_on_submit():
        if form.email.data in database.User.get_all('email'):
            render.flash_error('A user account with theis email already exists')
        else:
            if signup_key is not None and signup_key == database.Attrs.get('signup_key'):
                auth_level = auth.VERIFIED
            else:
                render.flash_message('Your account has to be verified by an administrator before you can upload data')
                auth_level = auth.UNVERIFIED

            new_user = database.User.new_user(form.name.data, form.email.data, form.password.data, auth_level)
            render.flash_success('You have successfully signed up')
            logout_user()
            login_user(new_user)
            return render.redirect('main.search')

    return render.template('form.html', form=form, before_form="<h3>Create Account</h3>")

@user.route('/change_password', methods=['GET', 'POST'])
@auth.required(auth.DEACTIVATED)
def change_password():
    user = auth.current_user
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if database.User.verify_password(user, form.old_password.data):
            database.User.update_password(user, form.new_password.data)
            render.flash_success('Password Updated')
            render.redirect('main.search')
        else:
            render.flash_error('Invalid password')
    return render.template('form.html', form=form, before_form="<h3>Change password</h3>")

############
### Text ###
############
def login_text():
    return dict(
        after_form = f"""
        <br>
        Click [here]({render.url_for('user.signup')}) to sign up for account.""")




