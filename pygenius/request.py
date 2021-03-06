from aiohttp import ClientSession
from typing import Optional, Any

from .exceptions import HTTPException, GeniusException

BASE_URL = "https://api.genius.com"


class Base:
    def __init__(self) -> None:
        self.session: Optional[ClientSession] = None

    async def request(
        self,
        url: str,
        method: str,
        return_type: str,
        **kwargs: Any,
    ):
        if not self.session or self.session.closed:
            self.session = ClientSession()

        resp = await self.session.request(method, url, **kwargs)

        if resp.status == 200:
            return await getattr(resp, return_type)()

        else:
            raise HTTPException(resp.status, url)

    async def post(self, url: str, **kwargs: Any):
        if not self.session or self.session.closed:
            self.session = ClientSession()

        return await self.request(url, "POST", **kwargs)

    async def get(self, url: str, **kwargs: Any):
        if not self.session or self.session.closed:
            self.session = ClientSession()

        return await self.request(url, "GET", **kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.session:
            await self.session.close()


class GeniusRequest(Base):
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        super().__init__()

    async def auth(self, scopes: Optional[str]):
        query = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scopes": "+".join(scopes[:]),
        }

        resp = await self.post(
            f"{BASE_URL}/oauth/token", return_type="json", params=query
        )

        return resp["access_token"]

    async def send_request(self, endpoint, **kwargs):
        if endpoint == "/account":
            scopes = "me"
        else:
            scopes = ""

        if self.access_token is None:
            self.access_token = await self.auth(scopes)

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "User-Agent": "CompuServe Classic/1.22",
        }

        resp = await self.get(
            f"{BASE_URL}{endpoint}", return_type="json", headers=headers, **kwargs
        )

        if resp["meta"]["status"] == 200:
            return resp["response"]

        else:
            raise GeniusException(
                resp["meta"]["status"], f"{BASE_URL}{endpoint}", resp["meta"]["message"]
            )
