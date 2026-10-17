"""Post the next due tweet from tweets/queue/*.json to X.

Queue file format (one file per day, e.g. tweets/queue/2026-10-18.json):
  [{"id": "2026-10-18-1", "at": "2026-10-18T07:00:00+08:00", "text": "..."}, ...]

Posts at most ONE due tweet per run (oldest first) so a late GitHub run never
dumps several tweets at once. Tweets more than MAX_LATE_HOURS overdue are
skipped. Results are recorded in tweets/posted.json.

Needs env vars X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET.
"""
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "tweets" / "queue"
LOG = ROOT / "tweets" / "posted.json"
URL = "https://api.x.com/2/tweets"
MAX_LATE_HOURS = 3


def q(s):
    return urllib.parse.quote(str(s), safe="~-._")


def oauth_header(method, url):
    ck, cs = os.environ["X_API_KEY"], os.environ["X_API_SECRET"]
    tk, ts = os.environ["X_ACCESS_TOKEN"], os.environ["X_ACCESS_SECRET"]
    params = {
        "oauth_consumer_key": ck,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": tk,
        "oauth_version": "1.0",
    }
    param_str = "&".join(f"{q(k)}={q(v)}" for k, v in sorted(params.items()))
    base = "&".join([method.upper(), q(url), q(param_str)])
    key = f"{q(cs)}&{q(ts)}".encode()
    params["oauth_signature"] = base64.b64encode(hmac.new(key, base.encode(), hashlib.sha1).digest()).decode()
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(params.items()))


def post(text):
    body = json.dumps({"text": text}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Authorization": oauth_header("POST", URL),
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main():
    log = json.loads(LOG.read_text()) if LOG.exists() else {}
    now = dt.datetime.now(dt.timezone.utc)
    due = []
    for f in sorted(QUEUE.glob("*.json")):
        for item in json.loads(f.read_text()):
            if item["id"] in log:
                continue
            at = dt.datetime.fromisoformat(item["at"])
            if at <= now:
                due.append((at, item))
    due.sort(key=lambda x: x[0])
    changed = False
    for at, item in due:
        late = (now - at).total_seconds() / 3600
        if late > MAX_LATE_HOURS:
            log[item["id"]] = {"status": "skipped_late", "at": now.isoformat()}
            changed = True
            print("skipped (too late):", item["id"])
            continue
        if len(re.sub(r"https?://\S+", "x" * 23, item["text"])) > 280:  # X counts links as 23
            log[item["id"]] = {"status": "skipped_too_long", "at": now.isoformat()}
            changed = True
            print("skipped (over 280 chars):", item["id"])
            continue
        status, resp = post(item["text"])
        print("X API", status, resp)
        if status in (200, 201):
            log[item["id"]] = {"status": "posted", "tweet_id": resp["data"]["id"], "at": now.isoformat()}
        else:
            log[item["id"]] = {"status": f"error_{status}", "detail": str(resp)[:300], "at": now.isoformat()}
        changed = True
        break  # one tweet per run
    if changed:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    else:
        print("nothing due")
    # fail the job on an API error so it shows red in GitHub
    if any(v.get("status", "").startswith("error_") and v.get("at") == now.isoformat() for v in log.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
