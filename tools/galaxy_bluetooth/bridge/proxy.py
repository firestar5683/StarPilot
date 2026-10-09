"""Only proxies relative Galaxy requests to the fixed comma loopback endpoint."""
import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from protocol import MAX_BODY

REQUEST_HEADERS = {"content-type", "accept", "cookie", "range"}
RESPONSE_HEADERS = {"content-type", "content-range", "accept-ranges", "content-disposition"}
METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"}
MEDIA_PREFIXES = ("/video/", "/screen_recordings/", "/api/screen_recordings/download/", "/api/sentry/video/")
# StarPilot includes this binary learning history in its all-parameters endpoint.
# Galaxy's bundled UI never reads it and it is not a toggle in the settings catalog.
# Bound the upstream snapshot separately, then retain every other parameter within
# the existing BLE body limit. No parameter on the comma is modified.
PARAMS_SNAPSHOT_LIMIT = 8 * MAX_BODY
INTERNAL_PARAMS = {"LiveTorqueParameters"}


def validate_target(target):
    if not isinstance(target, str) or len(target) > 8192 or any(ord(c) < 32 for c in target):
        raise ValueError("Invalid request path")
    parsed = urllib.parse.urlsplit(target)
    decoded = urllib.parse.unquote(parsed.path)
    if parsed.scheme or parsed.netloc or parsed.fragment or not decoded.startswith("/"):
        raise ValueError("Only relative Galaxy paths are allowed")
    if "\\" in decoded or "//" in decoded or any(p in (".", "..") for p in decoded.split("/")):
        raise ValueError("Invalid path segments")
    if any(ord(c) < 32 for c in decoded) or "%" in decoded:
        raise ValueError("Invalid encoded path")
    if not (decoded.startswith("/api/") or decoded == "/assets/components/tools/device_settings_layout.json"):
        raise ValueError("Path is outside the Galaxy API")
    return target


def error_response(request_id, status, message):
    return {"id": request_id, "status": status, "headers": {"content-type": "application/json"},
            "body": base64.b64encode(json.dumps({"error": message}).encode()).decode()}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GalaxyProxy:
    def __init__(self, port=8082):
        if not 1 <= port <= 65535:
            raise ValueError("Invalid Galaxy port")
        self.base = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def handle(self, request):
        request_id = str(request.get("id", ""))
        try:
            if request.get("path") == "/_bridge/health" and request.get("method") == "GET":
                return {"id": request_id, "status": 200, "headers": {"content-type": "application/json"},
                        "body": base64.b64encode(b'{"protocol":1,"transport":"bluetooth","readStream":true}').decode()}
            target = validate_target(request.get("path"))
            method = request.get("method", "GET")
            if method not in METHODS:
                raise ValueError("Unsupported HTTP method")
            if target.split("?")[0].startswith(MEDIA_PREFIXES):
                return error_response(request_id, 501, "Video transfer is not supported by this BLE prototype.")
            body = base64.b64decode(request.get("body", ""), validate=True)
            if len(body) > MAX_BODY:
                return error_response(request_id, 413, "Upload exceeds the 1 MiB BLE limit.")
            supplied_headers = request.get("headers", {})
            if not isinstance(supplied_headers, dict):
                raise ValueError("Invalid headers")
            headers = {str(k): str(v) for k, v in supplied_headers.items() if str(k).lower() in REQUEST_HEADERS}
            if any("\r" in v or "\n" in v for v in headers.values()):
                raise ValueError("Invalid header value")
            upstream = urllib.request.Request(self.base + target, data=body if body else None, method=method, headers=headers)
            try:
                response = self.opener.open(upstream, timeout=35)
            except urllib.error.HTTPError as e:
                response = e
            with response:
                content_type = response.headers.get("content-type", "")
                if content_type.startswith(("video/", "multipart/x-mixed-replace")):
                    return error_response(request_id, 501, "Continuous media streams are not supported over this BLE bridge.")
                if content_type.startswith("text/event-stream") and target.split("?")[0] not in ("/api/routes", "/api/screen_recordings/list"):
                    return error_response(request_id, 501, "Continuous event streams are not supported; use a snapshot endpoint.")
                compact_parameters = method == "GET" and target.split("?")[0] == "/api/params/all"
                read_limit = PARAMS_SNAPSHOT_LIMIT if compact_parameters else MAX_BODY
                chunks, total = [], 0
                deadline = time.monotonic() + 35
                while total <= read_limit:
                    if time.monotonic() > deadline:
                        return error_response(request_id, 504, "Galaxy response took too long to complete.")
                    chunk = response.read1(min(65536, read_limit + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                data = b"".join(chunks)
                if len(data) > read_limit:
                    return error_response(request_id, 413, "Galaxy response exceeds the bounded bridge read limit.")
                if compact_parameters and response.status == 200:
                    try:
                        values = json.loads(data)
                    except (ValueError, UnicodeDecodeError):
                        return error_response(request_id, 502, "Galaxy returned invalid settings JSON.")
                    if not isinstance(values, dict):
                        return error_response(request_id, 502, "Galaxy returned an invalid settings snapshot.")
                    data = json.dumps({k: v for k, v in values.items() if k not in INTERNAL_PARAMS},
                                      separators=(",", ":"), ensure_ascii=False).encode()
                if len(data) > MAX_BODY:
                    return error_response(request_id, 413, "Response exceeds the 1 MiB BLE limit.")
                if 300 <= response.status < 400:
                    return error_response(request_id, 502, "Galaxy redirected the request; redirects are disabled in the BLE bridge.")
                return {"id": request_id, "status": response.status,
                        "headers": {k.lower(): v for k, v in response.headers.items() if k.lower() in RESPONSE_HEADERS},
                        "body": base64.b64encode(data).decode()}
        except (ValueError, TypeError, KeyError) as e:
            return error_response(request_id, 400, str(e))
        except Exception:
            return error_response(request_id, 502, "Galaxy did not answer on the comma's loopback port. Check that Galaxy is running.")
