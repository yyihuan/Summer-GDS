from __future__ import annotations

from summer_gds.gui.server import create_app


TOKEN = "test-token"


def test_index_is_local_static_shell(tmp_path):
    app = create_app(session_token=TOKEN, temp_root=tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Summer GDS" in html
    assert TOKEN in html
    assert "http://" not in html
    assert "https://" not in html
    assert "cdn" not in html.lower()
    assert "/static/style.css" in html
    assert "/static/app.js" in html
