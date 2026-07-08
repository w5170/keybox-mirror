#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TAKR_API_BASE = "https://keybox.kowx712.cc/api"
TAKR_LIST_URL = f"{TAKR_API_BASE}/keyboxes?search=&sort=status&page=1&limit=50"
TAKR_PAGE_URL = "https://keybox.kowx712.cc/zh-CN"
TAKR_SITE_KEY = "0x4AAAAAADfdLPEQDYpW8Bcj"

CAPMONSTER_CREATE = "https://api.capmonster.cloud/createTask"
CAPMONSTER_RESULT = "https://api.capmonster.cloud/getTaskResult"
CAPSOLVER_CREATE = "https://api.capsolver.com/createTask"
CAPSOLVER_RESULT = "https://api.capsolver.com/getTaskResult"

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def request_json(url, method="GET", data=None, headers=None, timeout=60):
    body = None
    hdrs = {"User-Agent": DEFAULT_UA, "Accept": "application/json, text/plain, */*"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def request_bytes(url, method="GET", data=None, headers=None, timeout=90):
    hdrs = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def latest_valid_keybox():
    data = request_json(TAKR_LIST_URL)
    for item in data.get("keyboxes", []):
        if item.get("status") == "valid":
            return item
    raise RuntimeError("No status=valid keybox found in TAKR list")


def poll_result(result_url, client_key, task_id, provider):
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(5)
        result = request_json(result_url, method="POST", data={"clientKey": client_key, "taskId": task_id})
        if result.get("errorId") not in (0, None):
            raise RuntimeError(f"{provider} getTaskResult failed: {result.get('errorDescription') or result.get('errorCode') or result}")
        if result.get("status") == "ready":
            solution = result.get("solution") or {}
            token = solution.get("token") or result.get("token")
            user_agent = solution.get("userAgent") or result.get("userAgent") or DEFAULT_UA
            if not token:
                raise RuntimeError(f"{provider} ready result has no token: {result}")
            return token, user_agent
    raise TimeoutError(f"{provider} solving timed out")


def solve_turnstile_capmonster(client_key, page_url):
    create_payload = {
        "clientKey": client_key,
        "task": {
            "type": "TurnstileTask",
            "websiteURL": page_url,
            "websiteKey": TAKR_SITE_KEY,
        },
    }
    create = request_json(CAPMONSTER_CREATE, method="POST", data=create_payload)
    if create.get("errorId") not in (0, None):
        raise RuntimeError(f"CapMonster createTask failed: {create.get('errorDescription') or create.get('errorCode') or create}")
    task_id = create.get("taskId")
    if not task_id:
        raise RuntimeError(f"CapMonster createTask returned no taskId: {create}")
    return poll_result(CAPMONSTER_RESULT, client_key, task_id, "CapMonster")


def solve_turnstile_capsolver(client_key, page_url):
    create_payload = {
        "clientKey": client_key,
        "task": {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": TAKR_SITE_KEY,
        },
    }
    create = request_json(CAPSOLVER_CREATE, method="POST", data=create_payload)
    if create.get("errorId") not in (0, None):
        raise RuntimeError(f"CapSolver createTask failed: {create.get('errorDescription') or create.get('errorCode') or create}")
    task_id = create.get("taskId")
    if not task_id:
        raise RuntimeError(f"CapSolver createTask returned no taskId: {create}")
    return poll_result(CAPSOLVER_RESULT, client_key, task_id, "CapSolver")


def solve_turnstile(page_url):
    provider = os.environ.get("SOLVER_PROVIDER", "").strip().lower()
    capsolver_key = os.environ.get("CAPSOLVER_CLIENT_KEY", "").strip()
    capmonster_key = os.environ.get("CAPMONSTER_CLIENT_KEY", "").strip()

    if provider == "capsolver" or (capsolver_key and provider != "capmonster"):
        if not capsolver_key:
            raise RuntimeError("SOLVER_PROVIDER=capsolver but CAPSOLVER_CLIENT_KEY is missing")
        print("Using CapSolver")
        return solve_turnstile_capsolver(capsolver_key, page_url)

    if provider == "capmonster" or capmonster_key:
        if not capmonster_key:
            raise RuntimeError("SOLVER_PROVIDER=capmonster but CAPMONSTER_CLIENT_KEY is missing")
        print("Using CapMonster")
        return solve_turnstile_capmonster(capmonster_key, page_url)

    raise RuntimeError("Missing solver secret: set CAPSOLVER_CLIENT_KEY or CAPMONSTER_CLIENT_KEY")


def takr_download_url(identity, token, page_url, user_agent):
    headers = {
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cf-Turnstile-Token": token,
        "Origin": "https://keybox.kowx712.cc",
        "Referer": page_url,
    }
    raw = request_bytes(
        f"{TAKR_API_BASE}/keyboxes/{identity}/download",
        method="POST",
        data=b"",
        headers=headers,
    )
    data = json.loads(raw.decode("utf-8"))
    url = data.get("url")
    if not url:
        raise RuntimeError(f"TAKR download API returned no url: {data}")
    return url


def validate_keybox(xml_bytes):
    markers = [
        b"<AndroidAttestation",
        b"<Keybox",
        b"<PrivateKey",
        b"<CertificateChain",
    ]
    return all(m in xml_bytes for m in markers)


def main():
    item = latest_valid_keybox()
    identity = item["identity"]
    page_url = f"{TAKR_PAGE_URL}?identity={identity}"
    print(f"Latest valid identity: {identity}")

    token, user_agent = solve_turnstile(page_url)
    url = takr_download_url(identity, token, page_url, user_agent)
    xml = request_bytes(url, headers={"User-Agent": user_agent})

    if not validate_keybox(xml):
        raise RuntimeError("Downloaded file is not a valid keybox.xml")

    with open("keybox.xml", "wb") as f:
        f.write(xml)

    metadata = {
        "source": "https://keybox.kowx712.cc/zh-CN",
        "identity": identity,
        "status": item.get("status"),
        "created_at": item.get("created_at"),
        "nearest_expiry": item.get("nearest_expiry"),
        "key_format": item.get("key_format"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open("metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("keybox.xml updated")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}", file=sys.stderr)
        raise
