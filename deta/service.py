import os
import json
import socket
import http.client
import struct
import urllib.error
from typing import Mapping, MutableMapping, Optional, Tuple, Union

JSON_MIME = "application/json"


class _Service:
    def __init__(
        self,
        project_key: str,
        project_id: str,
        host: str,
        name: str,
        timeout: int,
        keep_alive: bool = True,
    ):
        self.project_key = project_key
        self.base_path = f"/v1/{project_id}/{name}"
        self.host = host
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.client = http.client.HTTPSConnection(host, timeout=timeout) if keep_alive else None

    def _is_socket_closed(self):
        if not self.client.sock:
            return True
        fmt = "B" * 7 + "I" * 21
        tcp_info = struct.unpack(
            fmt, self.client.sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 92)
        )
        # 8 = CLOSE_WAIT
        if len(tcp_info) > 0 and tcp_info[0] == 8:
            return True
        return False

    def _request(
        self,
        path: str,
        method: str,
        data: Optional[Union[str, bytes, dict]] = None,
        headers: Optional[MutableMapping[str, str]] = None,
        content_type: Optional[str] = None,
        stream: bool = False,
    ) -> Tuple[int, Optional[dict]]:
        url = self.base_path + path
        headers = headers or {}
        headers["X-Api-Key"] = self.project_key
        if content_type:
            headers["Content-Type"] = content_type
        if not self.keep_alive:
            headers["Connection"] = "close"

        # close connection if socket is closed
        # fix for a bug in lambda
        try:
            if (
                self.client
                and os.environ.get("DETA_RUNTIME") == "true"
                and self._is_socket_closed()
            ):
                self.client.close()
        except Exception:
            pass

        # send request
        body = json.dumps(data) if content_type == JSON_MIME else data

        # response
        res = self._send_request_with_retry(method, url, headers, body)
        status = res.status

        if status not in [200, 201, 202, 207]:
            # need to read the response so subsequent requests can be sent on the client
            res.read()
            if not self.keep_alive:
                self.client.close()
            # return None if not found
            if status == 404:
                return status, None
            raise urllib.error.HTTPError(url, status, res.reason, res.headers, res.fp)

        # if stream return the response and client without reading and closing the client
        if stream:
            return status, res

        # return json if application/json
        payload = (
            json.loads(res.read()) if JSON_MIME in res.getheader("content-type") else res.read()
        )

        if not self.keep_alive:
            self.client.close()
        return status, payload

    def _send_request_with_retry(
        self,
        method: str,
        url: str,
        headers: Optional[Mapping[str, str]] = None,
        body: Optional[Union[str, bytes, dict]] = None,
        retry: int = 2,  # try at least twice to regain a new connection
    ):
        headers = headers if headers is not None else {}
        reinit_connection = False
        while retry > 0:
            try:
                if not self.keep_alive or reinit_connection:
                    self.client = http.client.HTTPSConnection(host=self.host, timeout=self.timeout)

                self.client.request(
                    method,
                    url,
                    headers=headers,
                    body=body,
                )
                res = self.client.getresponse()
                return res
            except http.client.RemoteDisconnected:
                reinit_connection = True
                retry -= 1
