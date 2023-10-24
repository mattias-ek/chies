from functools import wraps
from flask_login import current_user

import render

DEACTIVATED = 1
UNVERIFIED = 2
VERIFIED = 3
MODERATOR = 20
ADMIN = 50
ROLE = dict(deactivated = DEACTIVATED,
            unverified = UNVERIFIED,
            verified = VERIFIED,
            moderator = MODERATOR,
            admin = ADMIN)

__all__ = ['DEACTIVATED', 'UNVERIFIED', 'VERIFIED', 'MODERATOR', 'ADMIN', 'ROLE',
           'required', 'verified_required', 'moderator_required', 'admin_required']

def role_description(auth_level):
    for k, v in ROLE.items():
        if v == auth_level:
            return k
    else:
        return auth_level

def required(auth_level):
    def wrap_func(func):
        @wraps(func)
        def check_auth_level(*args, **kwargs):
            if not current_user.is_authenticated:
                render.flash_error('You must be logged in to view this page')
                return render.redirect('main.search')
            elif current_user.auth_level >= auth_level:
                return func(*args, **kwargs)
            else:
                if current_user.auth_level == DEACTIVATED:
                    render.flash_error('This account has been deactivated')
                if current_user.auth_level == UNVERIFIED:
                    render.flash_error('This account has not yet been verified by an moderator')

                render.flash_error('You are not authorised to view this page')
                return render.redirect('main.search')

        return check_auth_level

    if type(auth_level) is int:
        return wrap_func
    else:
        raise ValueError('Invalid auth_level')


def verified_required(func):
    return required(ROLE['verified'])(func)

def moderator_required(func):
    return required(ROLE['moderator'])(func)

def admin_required(func):
    return required(ROLE['admin'])(func)


