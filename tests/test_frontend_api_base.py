def test_api_base_uses_same_origin_and_supports_local_development():
    source = __import__("pathlib").Path("frontend/app.js").read_text()

    assert 'const API_BASE = window.location.origin + "/api/v1";' in source
