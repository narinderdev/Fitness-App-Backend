def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Fitness API running"
    assert payload["status"] == "success"
    assert payload["data"]["service"] == "fitness-backend"


def test_api_info_endpoint(client):
    response = client.get("/api-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "API information"
    assert payload["status"] == "success"
    assert payload["data"]["docs_url"] == "/docs"
    assert payload["data"]["service"] == "Fitness Backend"
