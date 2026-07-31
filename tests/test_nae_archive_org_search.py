from unittest.mock import MagicMock, patch

from NAE.collectors.archive_org import search


def _mock_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status.side_effect = None
    return resp


def test_search_keyword_parses_docs():
    payload = {
        "response": {
            "docs": [
                {
                    "identifier": "john_gill_body_divinity",
                    "title": "Body of Divinity",
                    "creator": "John Gill",
                    "year": "1770",
                    "language": "eng",
                    "licenseurl": "https://creativecommons.org/publicdomain/mark/1.0/",
                    "publicdate": "2010-01-01",
                    "mediatype": "texts",
                    "downloads": 42,
                    "collection": ["americana"],
                }
            ]
        }
    }
    with patch("NAE.collectors.archive_org.search.requests.get", return_value=_mock_response(payload)):
        results = search.search_keyword("Baptist", rows=10)
    assert len(results) == 1
    assert results[0].identifier == "john_gill_body_divinity"
    assert results[0].downloads == 42


def test_search_keyword_retries_on_server_error():
    payload = {"response": {"docs": []}}
    fail_resp = _mock_response({}, status=500)
    ok_resp = _mock_response(payload)
    with patch("NAE.collectors.archive_org.search.requests.get", side_effect=[fail_resp, ok_resp]), \
         patch("NAE.collectors.archive_org.search.time.sleep"):
        results = search.search_keyword("Baptist", rows=10, retry=2)
    assert results == []


def test_search_keyword_raises_after_exhausting_retries():
    import requests as real_requests
    with patch("NAE.collectors.archive_org.search.requests.get",
               side_effect=real_requests.Timeout("timeout")), \
         patch("NAE.collectors.archive_org.search.time.sleep"):
        try:
            search.search_keyword("Baptist", rows=10, retry=2)
            assert False, "expected exception"
        except real_requests.Timeout:
            pass
