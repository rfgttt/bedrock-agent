from __future__ import annotations

import httpx
import pytest

from bedrock_agent.capabilities.web import SafeWebClient


def public_resolver(_host: str) -> list[str]:
    return ["93.184.216.34"]


def test_web_client_blocks_private_network() -> None:
    client = SafeWebClient(resolver=lambda _host: ["127.0.0.1"])
    with pytest.raises(PermissionError):
        client.validate_url("http://localhost:8000/admin")


def test_web_search_and_read_use_untrusted_public_text() -> None:
    search_html = '''
    <html><body>
      <a class="result__a" href="https://example.com/article">Python Testing Guide</a>
    </body></html>
    '''
    page_html = "<html><style>bad</style><body><h1>Guide</h1><p>Use pytest carefully.</p></body></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "html.duckduckgo.com":
            return httpx.Response(200, text=search_html, headers={"content-type": "text/html"}, request=request)
        return httpx.Response(200, text=page_html, headers={"content-type": "text/html"}, request=request)

    http_client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    client = SafeWebClient(client=http_client, resolver=public_resolver)

    results = client.search("pytest", limit=3)
    page = client.read_page(results[0]["url"])

    assert results[0]["title"] == "Python Testing Guide"
    assert page["text"] == "Guide Use pytest carefully."


def test_web_search_falls_back_to_bing_when_duckduckgo_times_out() -> None:
    bing_html = '''
    <html><body><ol>
      <li class="b_algo"><h2><a href="https://example.com/pytest">pytest official docs</a></h2></li>
    </ol></body></html>
    '''

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "html.duckduckgo.com":
            raise httpx.ConnectTimeout("blocked", request=request)
        return httpx.Response(200, text=bing_html, headers={"content-type": "text/html"}, request=request)

    client = SafeWebClient(
        client=httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False),
        resolver=public_resolver,
    )

    results = client.search("pytest", limit=3)

    assert results == [
        {"title": "pytest official docs", "url": "https://example.com/pytest", "provider": "Bing"}
    ]
