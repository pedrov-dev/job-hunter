import asyncio

import httpx

from src.discovery import CareerPageDiscovery


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, url="https://example.com"):
        self.status_code = status_code
        self._payload = payload
        self.request = httpx.Request("GET", url)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class FakeClient:
    def __init__(self, response):
        self._response = response
        self.last_url = None

    async def get(self, url):
        self.last_url = url
        return self._response

    async def post(self, url, json):
        self.last_url = url
        return self._response


def test_lever_404_returns_empty_list():
    discovery = CareerPageDiscovery(company_targets=[])
    client = FakeClient(FakeResponse(status_code=404, payload="not found"))

    jobs = asyncio.run(discovery._lever(client, "wandb", seen=set()))

    assert jobs == []


def test_greenhouse_unexpected_payload_returns_empty_list():
    discovery = CareerPageDiscovery(company_targets=[])
    client = FakeClient(FakeResponse(payload="oops"))

    jobs = asyncio.run(discovery._greenhouse(client, "bitso", seen=set()))

    assert jobs == []


def test_ashby_normalizes_job_board_payload():
    discovery = CareerPageDiscovery(company_targets=[])
    client = FakeClient(
        FakeResponse(
            payload={
                "data": {
                    "jobBoard": {
                        "jobPostings": [
                            {
                                "title": "ML Engineer",
                                "locationName": "Remote - Mexico",
                                "isRemote": True,
                                "externalLink": "https://example.com/job/1",
                            }
                        ]
                    }
                }
            }
        )
    )

    jobs = asyncio.run(discovery._ashby(client, "cohere", seen=set()))

    assert len(jobs) == 1
    assert jobs[0].title == "ML Engineer"
    assert jobs[0].remote is True


def test_slug_override_is_used_for_fetch_url():
    discovery = CareerPageDiscovery(company_targets=[])
    client = FakeClient(FakeResponse(payload=[]))

    asyncio.run(discovery._lever(client, "wandb", seen=set()))

    assert "weightsbiases" in client.last_url
