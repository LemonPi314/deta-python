import os
import json
import urllib.error
import urllib.request
from typing import Optional, Sequence, Union

from .base import Base  # noqa: F401
from ._async.client import AsyncBase  # noqa: F401
from .drive import Drive  # noqa: F401
from .utils import _set_project_key_id

try:
    from detalib.app import App  # type: ignore

    app = App()
except ImportError:
    pass

__version__ = "1.1.0"


def init(project_key: Optional[str] = None, project_id: Optional[str] = None):
    _set_project_key_id(project_key, project_id)


def send_email(
    to: Union[str, Sequence[str]],
    subject: str,
    message: str,
    charset: str = "utf-8",
):
    # FIXME: should function continue if these are not present?
    pid = os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    url = os.getenv("DETA_MAILER_URL")
    api_key = os.getenv("DETA_PROJECT_KEY")
    endpoint = f"{url}/mail/{pid}"

    if isinstance(to, str):
        to = [to]
    else:
        to = list(to)

    data = {
        "to": to,
        "subject": subject,
        "message": message,
        "charset": charset,
    }
    headers = {"X-API-Key": api_key}

    req = urllib.request.Request(endpoint, json.dumps(data).encode("utf-8"), headers)

    try:
        resp = urllib.request.urlopen(req)
        if resp.getcode() != 200:
            raise Exception(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise Exception(e.reason) from e
