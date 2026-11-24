"""Test de describe_error (scout/sources/utils.py) : la clé SerpAPI ne doit jamais apparaître
dans un message d'erreur (ticket #27). Aucun appel réseau : les réponses sont simulées.
Lancer : python -m unittest discover -s tests"""

import logging
import unittest
from unittest import mock

import httpx

from scout.sources.indeed import IndeedSource
from scout.sources.serpapi import SerpAPISource
from scout.sources.utils import describe_error

FAKE_KEY = "FAKEKEY123"


def _failing_client(*args, **kwargs):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


class DescribeErrorTest(unittest.TestCase):
    def test_http_error_keeps_status_but_not_key(self):
        request = httpx.Request("GET", f"https://serpapi.com/search.json?q=x&api_key={FAKE_KEY}")
        response = httpx.Response(429, request=request)
        exc = httpx.HTTPStatusError("boom " + str(request.url), request=request, response=response)
        text = describe_error(exc)
        self.assertNotIn(FAKE_KEY, text)
        self.assertIn("429", text)

    def test_other_error_masks_key(self):
        exc = httpx.ConnectError(f"failed for url 'https://serpapi.com/search.json?api_key={FAKE_KEY}&q=x'")
        text = describe_error(exc)
        self.assertNotIn(FAKE_KEY, text)
        self.assertIn("api_key=***", text)


class SourcesDoNotLeakKeyTest(unittest.TestCase):
    def _run(self, source_cls, config):
        source = source_cls(config)
        with mock.patch.dict("os.environ", {"SERPAPI_KEY": FAKE_KEY}), \
             mock.patch.object(source_cls, "_make_client", _failing_client), \
             mock.patch("tenacity.nap.time.sleep"), \
             self.assertLogs(level=logging.WARNING) as logs:
            self.assertEqual(source.fetch(), [])
        output = "\n".join(logs.output)
        self.assertIn("429", output)
        self.assertNotIn(FAKE_KEY, output)

    def test_serpapi(self):
        self._run(SerpAPISource, {"serpapi_queries": [{"q": "engineer", "location": "Paris"}]})

    def test_indeed(self):
        self._run(IndeedSource, {"indeed_queries": [{"q": "engineer", "location": "Paris"}]})


if __name__ == "__main__":
    unittest.main()
