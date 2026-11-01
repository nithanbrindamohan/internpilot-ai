def test_application_private_to_owner(test_env,register,job):
    client,_=test_env
    alice=register('Alice'); bob=register('Bob')
    response=client.post('/api/applications',headers=alice['headers'],json={'job_id':job,'cover_letter':'My draft'})
    assert response.status_code==200,response.text
    appid=response.json()['id']
    assert len(client.get('/api/applications',headers=alice['headers']).json())==1
    assert client.get('/api/applications',headers=bob['headers']).json()==[]
    assert client.patch(f'/api/applications/{appid}',headers=bob['headers'],json={'status':'submitted'}).status_code==404
    assert client.patch(f'/api/applications/{appid}',headers=alice['headers'],json={'status':'ready_for_review'}).status_code==200
    assert client.patch(f'/api/applications/{appid}',headers=alice['headers'],json={'status':'arbitrary'}).status_code==400
