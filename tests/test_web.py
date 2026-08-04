from fastapi.testclient import TestClient

from marcus_cad.web import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_home_page_contains_draw_controls():
    response = client.get('/')
    assert response.status_code == 200
    assert 'GENERATE' in response.text
    assert 'SCOUT_CARD' in response.text


def test_draw_endpoint_returns_structured_result():
    response = client.post('/api/draw', json={
        'call': '(11) DBLS LT H STAR VS ODD COV 4',
        'card_type': 'SCOUT_CARD',
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload['source_call'] == '(11) DBLS LT H STAR VS ODD COV 4'
    assert isinstance(payload['success'], bool)
    assert 'files' in payload
