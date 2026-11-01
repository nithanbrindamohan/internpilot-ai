import hashlib

def test_registration_requires_valid_invite(test_env):
    client, _ = test_env
    response = client.post('/api/auth/register', json={
        'full_name':'Alice', 'email':'alice@example.com','password':'SafeTestPass123!', 'invite_code':'IP-NOT-REAL-CODE'})
    assert response.status_code == 403

def test_registration_and_reused_code(test_env, invite):
    client, db = test_env
    form = {'full_name':'Alice', 'email':'alice@example.com', 'password':'SafeTestPass123!', 'invite_code':invite}
    success = client.post('/api/auth/register', json=form)
    assert success.status_code == 200, success.text
    assert client.post('/api/auth/register', json={**form, 'email':'other@example.com'}).status_code == 403
    assert client.post('/api/auth/register', json=form).status_code == 409
    token = success.json()['access_token']
    assert client.get('/api/auth/me', headers={'Authorization':f'Bearer {token}'}).status_code == 200
    with db.connect() as conn:
        assert conn.execute('SELECT used_at FROM invite_codes').fetchone()['used_at'] is not None

def test_login_and_bad_password(test_env, register):
    client, _ = test_env
    person=register()
    assert client.post('/api/auth/login', json={'email':person['email'], 'password':'SafeTestPass123!'}).status_code == 200
    assert client.post('/api/auth/login', json={'email':person['email'], 'password':'wrongpassword'}).status_code == 401

def test_private_endpoints_require_token(test_env, job):
    client, _ = test_env
    for url in ['/api/auth/me','/api/profile','/api/jobs','/api/applications',f'/api/jobs/{job}']:
        assert client.get(url).status_code == 401

def test_tampered_token_is_rejected(test_env, register):
    client,_ = test_env
    token = register()['token']
    assert client.get('/api/profile', headers={'Authorization':'Bearer '+token+'x'}).status_code == 401
