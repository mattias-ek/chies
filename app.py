from flask import Flask
from flask_wtf import CSRFProtect
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager

import database, auth, config


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(config.Config)
    login_manager = LoginManager()
    login_manager.anonymous_user = database.AnonymousUser
    
    import pages
    app.register_blueprint(pages.main.main)
    app.register_blueprint(pages.dm.dm, url_prefix='/dm')
    app.register_blueprint(pages.user.user, url_prefix='/user')
    app.register_blueprint(pages.admin.admin, url_prefix='/admin')
    
    csrf = CSRFProtect(app)
    bootstrap = Bootstrap5(app)
    login_manager.init_app(app)
    database.init(app)
    
    @app.context_processor
    def inject_user_roles():
        return {'user_role': auth.ROLE}
    
    @login_manager.user_loader
    def load_user(user_id):
        return database.User.get_one(id=int(user_id), or_none=True)
        
    return app


create_app()












