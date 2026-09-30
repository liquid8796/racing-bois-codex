"""Bounded direct V3 transport; bearer values and vendor messages never escape."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://openapi.tripo3d.ai/v3"


class ApiFailure(Exception):
    def __init__(self, *, http_status=None, code=None, definitive_rejection=False):
        super().__init__("Tripo request rejected." if definitive_rejection else "Tripo request outcome unavailable; do not retry a submission.")
        self.http_status = http_status
        self.code = code
        self.definitive_rejection = definitive_rejection

    def summary(self):
        return {"httpStatus": self.http_status, "code": self.code, "definitiveRejection": self.definitive_rejection}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ApiFailure()


def api_call(key, method, route, body=None, content_type=None):
    headers = {"Authorization": "Bearer " + key, "Accept": "application/json"}
    if isinstance(body, dict):
        body = json.dumps(body, allow_nan=False).encode("utf-8")
        content_type = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    request = Request(BASE_URL + route, data=body, method=method, headers=headers)
    status = None
    try:
        with build_opener(NoRedirect()).open(request, timeout=120) as response:
            status, raw = response.status, response.read(1024 * 1024 + 1)
    except HTTPError as error:
        status = error.code
        try:
            raw = error.read(1024 * 1024 + 1)
        except (URLError, TimeoutError, OSError):
            raise ApiFailure(http_status=status) from None
        finally:
            error.close()
    except (URLError, TimeoutError, OSError):
        raise ApiFailure() from None
    try:
        payload = json.loads(raw) if len(raw) <= 1024 * 1024 else None
    except (ValueError, UnicodeError):
        payload = None
    code = payload.get("code") if isinstance(payload, dict) else None
    code = code if isinstance(code, int) and not isinstance(code, bool) else None
    if status != 200 or code != 0:
        rejected = code is not None and code != 0 and status in {200, 400, 401, 403, 409, 422, 429}
        raise ApiFailure(http_status=status, code=code, definitive_rejection=rejected)
    if not isinstance(payload.get("data"), dict):
        raise ApiFailure(http_status=status, code=code)
    return payload["data"]
