def test_profile_save_and_account_isolation(test_env, register):
    client,_=test_env
    alice=register('Alice'); bob=register('Bob')
    payload = {'full_name':'Alice Example','university':'Example University','program':'Computer Science','graduation_year':'2028', 'location':'Ontario', 'work_authorization':'Canada', 'skills':['Python','React']}
    response=client.put('/api/profile',json=payload,headers=alice['headers'])
    assert response.status_code==200, response.text
    assert client.get('/api/profile',headers=alice['headers']).json()['skills']==['Python','React']
    assert client.get('/api/profile',headers=bob['headers']).json()['skills']==[]
    assert client.get('/api/profile',headers=bob['headers']).json()['full_name']=='Bob'

def test_resume_upload_validation_and_isolation(test_env,register):
    client,_=test_env
    alice=register('Alice');bob=register('Bob')
    text=b'Python React software engineering student resume\nUniversity example projects'
    response=client.post('/api/profile/resume',headers=alice['headers'],files={'file':('resume.txt',text,'text/plain')})
    assert response.status_code==200,response.text
    assert client.get('/api/profile',headers=alice['headers']).json()['has_resume'] is True
    assert client.get('/api/profile',headers=bob['headers']).json()['has_resume'] is False
    bad=client.post('/api/profile/resume',headers=alice['headers'],files={'file':('malware.exe',b'bad','application/octet-stream')})
    assert bad.status_code==400
    empty=client.post('/api/profile/resume',headers=alice['headers'],files={'file':('empty.txt',b'','text/plain')})
    assert empty.status_code==400
