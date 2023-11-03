import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
instancedir = os.path.join(basedir, 'instance')
backupdir = os.path.join(instancedir, 'backups')
load_dotenv(os.path.join(instancedir, 'chies.env'))
db_path = os.path.join(instancedir, 'database.db')
test_db_path = os.path.join(basedir, 'tests', 'files', 'testdb.db')

class Config:
    FLASK_APP = os.environ.get("FLASK_APP")
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG")
    SECRET_KEY = os.environ.get('SECRET_KEY')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY')
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY')
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}"


class Test(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{test_db_path}"