import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
instancedir = os.path.join(basedir, 'instance')
backupdir = os.path.join(instancedir, 'backups')
load_dotenv(os.path.join(instancedir, '.env'))

class Config:
    FLASK_APP = os.environ.get("FLASK_APP")
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG")
    SECRET_KEY = os.environ.get('SECRET_KEY')
    RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY')
    RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY')
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(instancedir, 'database.db')}"