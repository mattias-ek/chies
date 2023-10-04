from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import UserMixin, AnonymousUserMixin
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash
import re, datetime

import auth
import database

basedir = os.path.abspath(os.path.dirname(__file__))

db = SQLAlchemy()
_app = None

"""
How to query

Data.query.filter(Data.element == 'Pd')
same as: Data.query.filter_by(element='pd')

Data.query(Data.query.filter(Data.element.in_([list])


"""
# <link href="https://unpkg.com/gridjs/dist/theme/mermaid.min.css" rel="stylesheet" />
def init(app):
    db.init_app(app)
    globals()['_app'] = app

def add(model_item):
    db.session.add(model_item)

def commit():
    db.session.commit()

def with_app_context(func):
    @wraps(func)
    def call_func_with_context(*args, **kwargs):
        if _app is None:
            raise RuntimeError('An app instance has not been initialised')
        else:
            with _app.app_context():
                return func(*args, **kwargs)
    return call_func_with_context

def _get_table_field(default_table, name):
    def get_table(name):
        table = globals().get(name, None)
        if not issubclass(table, db.Model):
            raise ValueError(f"'{name}' is not a valid Table")
        return table

    def get_column(table, name):
        if name not in [c.key for c in table.__table__.columns]:
            raise ValueError(f"'{name}' is not a column of table '{table}'")
        else:
            return getattr(table, name)

    if type(name) is not str:
        raise TypeError('name must be a string')

    name = name.split('.', 1)

    if len(name) == 1:
        if name[0][0].islower():
            table = default_table
            column = get_column(table, name[0])
        else:
            table = get_table(name[0])
            column = None
    else:
        table = get_table(name[0])
        column = get_column(table, name[1])

    return table, column

class NamedDict(dict):
    def __getattr__(self, item):
        return self.__getitem__(item)

# To store users login stuff
class AnonymousUser(AnonymousUserMixin):
    auth_level = 0


class ModelMixin:
    @classmethod
    def get_query(cls, what=None, **where):
        # What
        if what is None:
            scalar = True
            query = db.select(cls)
        else:
            if isinstance(what, (list, tuple)):
                scalar = False
            else:
                scalar = True
                what = (what,)

            join = []
            items = []
            for w in what:
                table, column = _get_table_field(cls, w)
                if table is not cls:
                    join.append(table)
                items.append(column or table)

            query = db.select(*items)
            for j in join:
                query = query.join(j)

        # Where
        for key, value in where.items():
            if key.endswith('_eq'):
                query = query.where(getattr(cls, key.removesuffix('_eq')) == value)
            elif key.endswith('_in'):
                query = query.where(getattr(cls, key.removesuffix('_in')).in_(value))
            elif value is not None:
                if type(value) is list:  # in
                    if len(value) > 0:
                        query = query.where(getattr(cls, key).in_(value))
                elif type(value) is not str or (type(value) is str and len(value)) > 1:  # eq
                    query = query.where(getattr(cls, key) == value)

        return query, scalar

    @classmethod
    @with_app_context
    def get_all(cls, what=None, *, distinct=False, **where):
        query, scalar = cls.get_query(what, **where)

        # Distinct
        if distinct is True:
            query = query.distinct()

        result = db.session.execute(query)
        if scalar:
            result = result.scalars()

        return result.all()


    @classmethod
    @with_app_context
    def get_one(cls, what=None, *, or_none=False, **where):
        query, scalar = cls.get_query(what, **where)

        result = db.session.execute(query)
        if scalar:
            result = result.scalars()

        if or_none is True:
            return result.one_or_none()
        else:
            return result.one()

    @classmethod
    @with_app_context
    def new_entry(cls, current_user, **columns):
        new_item = cls(**columns)

        add(new_item)
        commit()

        Edit.new_created(current_user, new_item)
        commit()

        return cls.get_one(id = new_item.id)

    @classmethod
    @with_app_context
    def update_entry(cls, current_user, entry_id, **columns):
        item = cls.get_one(id = entry_id if type(entry_id) is int else entry_id.id)
        updated = []
        for column, new_value in columns.items():
            old_value = getattr(item, column)
            if new_value != old_value:
                setattr(item, column, new_value)
                Edit.new_edit(current_user, item, column, new_value, old_value)
                updated.append(column)
            else:
                continue
        add(item)
        commit()
        return updated

class Attrs(ModelMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(150), nullable=False, unique=True)

    value = db.Column(db.String(1024), nullable=False)

    @classmethod
    def get(cls, key, default=None, type=str):
        item = cls.get_one(key=key, or_none=True)
        if item is None:
            return default
        else:
            return type(item.value)

    @classmethod
    def set(cls, key, value):
        item = cls.get_one(key=key, or_none=True)
        if item is None:
            item = cls(key=key, value=str(value))
        else:
            item.value = str(value)

        add(item)
        commit()
        return cls.get_one('value', key=key)


class User(UserMixin, ModelMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)
    auth_level = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)

    @classmethod
    @with_app_context
    def new_user(cls, name, email, password, signup_key=None):
        if signup_key is not None and signup_key == Attrs.get('signup_key'):
            auth_level = auth.VERIFIED
        else:
            auth_level = auth.UNVERIFIED

        new_user = cls(name = name,
                       email = email,
                       password = generate_password_hash(password),
                       auth_level = auth_level)

        add(new_user)
        commit()
        database.Edit.new_created(new_user, new_user)
        commit()

        return cls.get_one(id=new_user.id)

    @classmethod
    def verify_password(cls, user_id, password):
        user = cls.get_one(id = user_id if type(user_id) is int else user_id.id)
        return check_password_hash(user.password, password)

    @classmethod
    def update_password(cls, user_id, new_password):
        user = cls.get_one(id=user_id if type(user_id) is int else user_id.id)

        user.password = generate_password_hash(new_password)
        add(user)
        database.Edit.new_edit(user, user, 'password', None, None)
        commit()


    def __repr__(self):
        return f'<User: {self.username}>'


class Edit(ModelMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.ForeignKey(User.id), nullable=False)

    datetime = db.Column(db.DateTime)
    table = db.Column(db.String(150), nullable=False)
    item_id = db.Column(db.Integer, nullable=False)

    column = db.Column(db.String(150))
    old_value = db.Column(db.String(150))
    new_value = db.Column(db.String(150))

    @classmethod
    def new_created(cls, user, item):
        new_edit = Edit(user_id=user.id,
                        datetime=datetime.datetime.now(),
                        table=item.__class__.__name__,
                        item_id=item.id,
                        column='CREATED')
        add(new_edit)
        return new_edit

    @classmethod
    def new_edit(cls, user, item, column, new_value, old_value):
        new_edit = Edit(user_id=user.id,
                        datetime=datetime.datetime.now(),
                        table=item.__class__.__name__,
                        item_id=item.id,
                        column=column,
                        new_value=str(new_value),
                        old_value=str(old_value))
        add(new_edit)
        return new_edit


class Citation(ModelMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.ForeignKey(User.id), nullable=False)

    authors = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    journal = db.Column(db.String(150), nullable=False)
    doi = db.Column(db.String(150), nullable=False, unique=True)
    ads = db.Column(db.String(150), nullable=False)

    @classmethod
    def get_citations(cls, sort = True, **where):
        results = cls.get_all(**where)
        if sort:
            results = sorted(results, key=lambda c: (c.year, c.authors, c.journal))

        citations = []
        for row in results:
            authors = row.authors.split(';')
            if len(authors) > 2:
                authors = f"{authors[0]}, et al."
            elif len(authors) == 2:
                authors = f"{authors[0]} & {authors[1]}"
            else:
                authors = authors[0]

            citations.append((row.id, f"{row.year} - {authors} - {row.journal} (doi:{row.doi})"))

        return citations


class Data(ModelMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    citation_id = db.Column(db.ForeignKey(Citation.id), nullable=False)
    creator_id = db.Column(db.ForeignKey(User.id), nullable=False)

    sample_type = db.Column(db.String(150), nullable=False)
    element = db.Column(db.String(2), nullable=False)

    @classmethod
    def get_search(cls, compress=True, headings_only = False, **where):
        headings = ['Authors', 'Year', 'Journal', 'Sample Type', 'Element', 'Link']
        if headings_only:
            return headings, []

        results = cls.get_all(**where)
        if results is None:
            return headings, []

        # get_all('citation_id', distinct=True, **where)
        #for each citation_id in citation_ids:
        # get_all(citation_id = citation_id)

        search_results = []
        citation_ids = []
        for result in results:
            if compress:
                if result.citation_id in citation_ids:
                    continue
                else:
                    citation_ids.append(result.citation_id)

                sampletypes = []
                elements = []
                for r in Data.get_all(citation_id=result.citation_id):
                    if r.sample_type not in sampletypes:
                        sampletypes.append(r.sample_type)
                    if r.element not in elements:
                        elements.append(r.element)

                sampletype = ', '.join(sampletypes)
                element = ', '.join(elements)
            else:
                sampletype = result.sample_type
                element = result.element

            citation = Citation.get_one(id=result.citation_id)
            link = f'<a href="https:doi.org/{citation.doi}">DOI</a>'
            if citation.ads:
                link += f'/<a href="{citation.ads}">ADS</a>'

            search_results.append((citation.authors,
                                  citation.year,
                                  citation.journal,
                                  sampletype,
                                  element,
                                  link))

        return headings, search_results







