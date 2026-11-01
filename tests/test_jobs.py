from app import main

def test_jobs_and_detail(test_env,register,job):
    client,_=test_env
    person=register()
    results=client.get('/api/jobs',headers=person['headers'])
    assert results.status_code==200 and any(x['id']==job for x in results.json())
    assert client.get(f'/api/jobs/{job}',headers=person['headers']).status_code==200
    assert client.get('/api/jobs/not-found',headers=person['headers']).status_code==404

def test_discovery_status_and_refresh_without_live_requests(test_env,register,monkeypatch):
    client,_=test_env
    person=register()
    test_job={'id':'new-job','source_key':'lever:example','source':'Lever','company':'Example','title':'Backend Developer Intern', 'location':'Toronto, Ontario','url':'https://example.com/new','description':'Java and SQL co-op internship','posted_at':'2026-10-30T00:00:00+00:00','employment_type':'Internship'}
    status={'source_key':'lever:example','company':'Example','source':'Lever','success':True,'jobs_found':1,'checked_at':'2026-10-31T00:00:00+00:00','error':''}
    monkeypatch.setattr(main,'discover_jobs',lambda:([test_job],[],[status]))
    result=client.post('/api/discover',headers=person['headers'])
    assert result.status_code==200,result.text
    assert result.json()['relevant']==1
    summary=client.get('/api/discover/status',headers=person['headers']).json()
    assert summary['healthy_sources']==1
    assert client.get('/api/jobs',headers=person['headers']).status_code==200
