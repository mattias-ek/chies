from app import create_app
import pytest
from werkzeug.security import generate_password_hash
from flask_login import  login_user
import database, auth, config
import re, csv, os

@database.with_app_context
def reset_db():
    db = database.db
    db.drop_all()
    db.create_all()

    admin = database.User(name='admin',
                         auth_level=auth.ADMIN,
                         email='admin@test.com',
                         password=generate_password_hash('password'))

    db.session.add(admin)
    db.session.commit()

    moderator = database.User(name='moderator',
                         auth_level=auth.MODERATOR,
                         email='moderator@test.com',
                         password=generate_password_hash('password'))

    db.session.add(moderator)
    db.session.commit()

    verified = database.User(name='verified',
                         auth_level=auth.VERIFIED,
                         email='verified@test.com',
                         password=generate_password_hash('password'))

    db.session.add(verified)
    db.session.commit()

    unverified = database.User(name='unverified',
                             auth_level=auth.UNVERIFIED,
                             email='unverified@test.com',
                             password=generate_password_hash('password'))

    db.session.add(unverified)
    db.session.commit()

    deactivated = database.User(name='deactivated',
                               auth_level=auth.DEACTIVATED,
                               email='deactivated@test.com',
                               password=generate_password_hash('password'))

    db.session.add(deactivated)
    db.session.commit()

    citations = {}
    with open('files/citations.csv', newline='', mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            citation = database.Citation.new_entry(admin.id,
                                                   creator_id=admin.id,
                                                   authors=row['authors'],
                                                   year=int(row['year']),
                                                   journal=row['journal'],
                                                   doi=re.search(".*(10[.][\d.]*[/].*)$", row['doi']).group(1),
                                                   ads=row['ads'])
            citations[row['citation_id']] = citation

    with open('files/data.csv', newline='', mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data = database.Data.new_entry(admin.id,
                                           creator_id=admin.id,
                                           citation_id=citations[row['citation_id']].id,
                                           sample_type=row['sample_type'],
                                           element=row['element'])

@pytest.fixture(scope='module')
def app():
    app = create_app(testing=True)
    reset_db()
    with app.app_context():
        yield app
    #yield app
    os.remove(config.test_db_path)

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def admin(app):
    with app.test_request_context():
        yield login_user(database.User.get_one(name='admin'))

@pytest.fixture()
def moderator(app):
    with app.test_request_context():
        yield login_user(database.User.get_one(name='moderator'))

@pytest.fixture()
def verified(app):
    with app.test_request_context():
        yield login_user(database.User.get_one(name='verified'))

@pytest.fixture()
def unverified(app):
    with app.test_request_context():
        yield login_user(database.User.get_one(name='unverified'))

@pytest.fixture()
def anonymous(app):
    with app.test_request_context():
        yield database.AnonymousUser

@pytest.fixture()
def modifies_db(app):
    yield database.db
    reset_db()

def test_search(client):
    response = client.get('/search')
    assert response.status_code == 200
    assert response.text.count('Authors') == 2 #Empty table

    response = client.post('/search')
    assert response.status_code == 200
    assert response.text.count('Authors') == 2 + 35  # All records

    response = client.post('/search', data=dict(element=['Mo']))
    assert response.status_code == 200
    assert response.text.count('Authors') == 2 + 4  # Only those containing Mo


def test_login(client, anonymous):
    assert auth.current_user.is_anonymous
    response = client.post('/user/login', data={'email': 'verified@test.com', 'password': 'password'}, follow_redirects=True)
    assert not auth.current_user.is_anonymous
    assert auth.current_user.auth_level == auth.VERIFIED
    assert response.request.base_url.endswith('search')


#TODO test for unverified

def test_dm_verified(client, verified, modifies_db):
    assert auth.current_user.auth_level == auth.VERIFIED

    citation_id, data_ids = dm_add(client, True)
    dm_edit(client, True, citation_id, data_ids[0])
    dm_remove(client, True, citation_id, data_ids[0])

    dm_edit(client, False, 1, 1)
    dm_remove(client, False, 1, 1)

    database.Data.get_search()

def test_dm_moderator(client, moderator, modifies_db):
    assert auth.current_user.auth_level == auth.MODERATOR

    citation_id, data_ids = dm_add(client, True)
    dm_edit(client, True, citation_id, data_ids[0])
    dm_remove(client, True, citation_id, data_ids[0])

    dm_edit(client, True, 1, 1)
    dm_remove(client, True, 1, 1)

    database.Data.get_search()

def dm_add(client, allowed):
    ncitations = len(database.Citation.get_all())
    ndata = len(database.Data.get_all())
    nedits = len(database.Edit.get_all())
    citation_id = ncitations + 1

    if not allowed:
        raise NotImplementedError()

    # Add citation
    citation = dict(authors='Test, A; Test, B',
                    year='2023',
                    journal='Nature Astronomy',
                    doi='10.1234/test',
                    ads='')

    response = client.post('/dm/add_citation', data=citation, follow_redirects=True)
    if allowed:
        assert response.request.base_url.endswith(f'add_data/{citation_id}')
        assert len(database.Citation.get_all()) == ncitations + 1
        assert len(database.Edit.get_all()) == nedits + 1
        ncitations += 1
        nedits += 1


    # Add data - single
    data1 = dict(sample_type='Wholerock',
                 element='pd')

    response = client.post(f'/dm/add_data/{citation_id}', data=data1, follow_redirects=True)
    if allowed:
        assert len(database.Data.get_all()) == ndata + 1
        assert len(database.Edit.get_all()) == nedits + 1
        ndata += 1
        nedits += 1

    # Add data -  multiple
    data2 = dict(citation = citation_id,
                sample_type='Wholerock',
                element='cd, ru')

    response = client.post(f'/dm/add_data', data=data2, follow_redirects=True)
    if allowed:
        assert len(database.Data.get_all()) == ndata + 2
        assert len(database.Edit.get_all()) == nedits + 2
        ndata += 2
        nedits += 2

    return citation_id, (ndata-2, ndata-1, ndata)

def dm_edit(client, allowed, citation_id, data_id):
    ncitations = len(database.Citation.get_all())
    ndata = len(database.Data.get_all())
    nedits = len(database.Edit.get_all())

    # Edit citation
    previous = database.Citation.get_one(id=citation_id).year
    response = client.post(f'/dm/edit_citation/{citation_id}', data={'year': 2024}, follow_redirects=True)
    if allowed:
        assert database.Citation.get_one(id = citation_id).year == 2024
        assert len(database.Citation.get_all()) == ncitations
        assert len(database.Edit.get_all()) == nedits + 1
        nedits += 1
    else:
        assert database.Citation.get_one(id = citation_id).year == previous
        assert len(database.Citation.get_all()) == ncitations
        assert len(database.Edit.get_all()) == nedits

    # Edit data
    previous = database.Data.get_one(id=data_id).element
    response = client.post(f'/dm/edit_data/{data_id}', data={'element': 'ge'}, follow_redirects=True)
    if allowed:
        assert database.Data.get_one(id=data_id).element == 'Ge'
        assert len(database.Data.get_all()) == ndata
        assert len(database.Edit.get_all()) == nedits + 1
        nedits += 1
    else:
        assert database.Data.get_one(id=data_id).element == previous
        assert len(database.Data.get_all()) == ndata
        assert len(database.Edit.get_all()) == nedits

def dm_remove(client, allowed, citation_id, data_id):
    ncitations = len(database.Citation.get_all())
    ndata = len(database.Data.get_all())
    nedits = len(database.Edit.get_all())

    ncitationdata = len(database.Data.get_all(citation_id=citation_id))
    assert ncitationdata > 1
    assert database.Data.get_one(id=data_id).citation_id == citation_id

    # Remove Data
    response = client.post(f'/dm/delete_data/{data_id}', data={'no': 'true'}, follow_redirects=True)
    assert len(database.Data.get_all()) == ndata
    assert len(database.Edit.get_all()) == nedits

    response = client.post(f'/dm/delete_data/{data_id}', data={'yes': 'true'}, follow_redirects=True)
    if allowed:
        assert len(database.Data.get_all()) == ndata - 1
        assert len(database.Edit.get_all()) == nedits + 1
        assert len(database.Data.get_all(citation_id=citation_id)) == ncitationdata - 1
        ndata -= 1
        nedits += 1
        ncitationdata -= 1
    else:
        assert len(database.Data.get_all()) == ndata
        assert len(database.Edit.get_all()) == nedits
        assert len(database.Data.get_all(citation_id=citation_id)) == ncitationdata

    # Remove citation
    response = client.post(f'/dm/delete_citation/{citation_id}', data={'no': 'true'}, follow_redirects=True)
    assert len(database.Citation.get_all()) == ncitations
    assert len(database.Edit.get_all()) == nedits

    response = client.post(f'/dm/delete_citation/{citation_id}', data={'yes': 'true'}, follow_redirects=True)
    if allowed:
        assert len(database.Citation.get_all()) == ncitations - 1
        assert len(database.Data.get_all()) == ndata - ncitationdata
        assert len(database.Edit.get_all()) == nedits + 1 + ncitationdata
        assert len(database.Data.get_all(citation_id=citation_id)) == 0
        ncitations -= 1
        ndata -= 2
        nedits += 3
        ncitationdata = 0
    else:
        assert len(database.Citation.get_all()) == ncitations
        assert len(database.Data.get_all()) == ndata
        assert len(database.Edit.get_all()) == nedits
        assert len(database.Data.get_all(citation_id=citation_id)) == ncitationdata

def test_citation_doi(client, verified, modifies_db):
    ncitations = len(database.Citation.get_all())

    # Add citation with doi
    citation = dict(authors='Test, A; Test, B',
                    year='2023',
                    journal='Nature Astronomy',
                    doi='something/10.1234/test',
                    ads='')

    ncitations += 1
    response = client.post('/dm/add_citation', data=citation, follow_redirects=True)
    assert response.request.base_url.endswith(f'add_data/{ncitations}')
    assert len(database.Citation.get_all()) == ncitations
    assert database.Citation.get_one(id=ncitations).doi == '10.1234/test'

    # Add citation
    citation['nodoi'] = True

    response = client.post('/dm/add_citation', data=citation, follow_redirects=True)
    assert response.request.base_url.endswith(f'add_citation')
    assert len(database.Citation.get_all()) == ncitations

    # Edit citation
    response = client.post(f'/dm/edit_citation/{ncitations}', data={'doi': '    10.987/abc'}, follow_redirects=True)
    assert database.Citation.get_one(id=ncitations).doi == '10.987/abc'
    assert len(database.Citation.get_all()) == ncitations

    # Add citation with url
    citation['doi'] = 'https://www.citation.com/page '

    ncitations += 1
    response = client.post('/dm/add_citation', data=citation, follow_redirects=True)
    assert response.request.base_url.endswith(f'add_data/{ncitations}')
    assert len(database.Citation.get_all()) == ncitations
    assert database.Citation.get_one(id=ncitations).doi == 'https://www.citation.com/page'

    # Add citation
    citation['nodoi'] = False

    response = client.post('/dm/add_citation', data=citation, follow_redirects=True)
    assert response.request.base_url.endswith(f'add_citation')
    assert len(database.Citation.get_all()) == ncitations

    # Edit citation
    # nodoi must be passsed. It defaults to the right value somehow in real life but not in this test.
    # Also the add citation test above fails if it is after this (But only if nodoi is given!) No clue why...
    # Somehow it sets nodoi to True and the the value in the citation is ignored.
    response = client.post(f'/dm/edit_citation/{ncitations}', data={'doi': '    https://www.reference.co.uk/page', 'nodoi': True}, follow_redirects=True)
    assert database.Citation.get_one(id=ncitations).doi == 'https://www.reference.co.uk/page'
    assert len(database.Citation.get_all()) == ncitations


