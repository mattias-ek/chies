from wtforms import SelectField, StringField, PasswordField, SubmitField, IntegerField
from wtforms import SelectMultipleField, EmailField
from wtforms import validators, ValidationError
from flask_wtf import FlaskForm
from flask_wtf.recaptcha import RecaptchaField


__all__ = ['SelectField', 'StringField', 'PasswordField', 'SubmitField', 'IntegerField',
           'SelectMultipleField', 'EmailField', 'RecaptchaField',
           'validators', 'ValidationError', 'FlaskForm',
           'IntSelectField', 'NewEntrySelectField']

enumerate_ = enumerate

class IntSelectField(SelectField):
    def __init__(self, label, choices, enumerate = True, **kwargs):
        if enumerate:
            choices = [(i, c) for i, c in enumerate_(choices)]

        default = kwargs.pop('default', None)
        if type(default) is str:
            default = choices[[c[1] for c in choices].index(default)][0]


        validators = kwargs.pop('validators', []) + [self._validator_]

        super().__init__(label, choices = choices, default=default, coerce=int, validators = validators, **kwargs)
        self.choice = None

    def _validator_(self, form, field):
        choices = dict(self.choices)
        if field.data not in choices.keys():
            raise ValidationError('Not a valid choice')
        else:
            self.choice = choices[field.data]


class NewEntrySelectField(SelectField):
    def __init__(self, label, new_entry_field, choices, **kwargs):
        validators = kwargs.pop('validators', []) + [self._validator_]
        self.new_entry_field = new_entry_field
        self.choice = None

        super().__init__(label, choices=choices, validators=validators, **kwargs)

    def _validator_(self, form, field):
        new_entry_field = getattr(form, self.new_entry_field)
        if field.data == field.choices[0]:
            if new_entry_field.data == '':
                raise ValidationError(f'The new entry field is empty')
            elif new_entry_field.data.lower() in [c.lower() for c in self.choices]:
                raise ValidationError("The new entry already exits in this list")
            self.choice = new_entry_field.data
        elif new_entry_field.data != '':
            raise ValidationError(
                f'Select {field.choices[0]} from this list above to create a new entry')
        else:
            self.choice = field.data
