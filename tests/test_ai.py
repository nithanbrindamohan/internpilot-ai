import sys
from types import SimpleNamespace
from app import main

class FakeCompletions:
    def create(self, **kwargs):
        content = ('{"score":87,"explanation":"Matches Python and React", "matched_skills":["Python"], "missing_skills":[], "suggested_actions":[]}'
                   if kwargs.get('response_format') else 'Dear Hiring Team, I am applying for this internship...')
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

class FakeOpenAI:
    def __init__(self, **kwargs):
        self.chat=SimpleNamespace(completions=FakeCompletions())

def test_ai_match_and_cover_letter_no_external_api(test_env,register,job,monkeypatch):
    client,_=test_env
    person=register()
    monkeypatch.setenv('OPENAI_API_KEY','test-fake-no-real-charges')
    monkeypatch.setitem(sys.modules,'openai',SimpleNamespace(OpenAI=FakeOpenAI))
    profile={'full_name':'Test Student','university':'Example University','program':'Software Engineering', 'graduation_year':'2028', 'location':'Ontario', 'work_authorization':'', 'skills':['Python','React']}
    assert client.put('/api/profile',headers=person['headers'],json=profile).status_code==200
    result=client.post(f'/api/jobs/{job}/ai-match',headers=person['headers'])
    assert result.status_code==200,result.text
    assert result.json()['score']==87
    letter=client.post(f'/api/jobs/{job}/cover-letter',headers=person['headers'])
    assert letter.status_code==200,letter.text
    assert 'Dear Hiring Team' in letter.json()['cover_letter']
