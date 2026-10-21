"""Collect blog topic ideas sent to George's private Telegram bot.

Runs in a GitHub Action every ~15 minutes. Reads new messages with the Bot API
(getUpdates), saves each text message from the owner as an idea in
ideas/ideas.json, and replies in Telegram to confirm.

The first person to message the bot becomes the owner (saved in
ideas/state.json); messages from anyone else are ignored.

Commands: /ideas lists waiting ideas. /start shows help.
Needs env var TELEGRAM_BOT_TOKEN.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDEAS = ROOT / "ideas" / "ideas.json"
STATE = ROOT / "ideas" / "state.json"
API = "https://api.telegram.org/bot" + os.environ["TELEGRAM_BOT_TOKEN"] + "/"


def call(method, **params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(API + method, data=data, timeout=30) as r:
        return json.loads(r.read())


def say(chat_id, text):
    try:
        call("sendMessage", chat_id=chat_id, text=text)
    except Exception as e:
        print("reply failed:", e)


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def main():
    IDEAS.parent.mkdir(exist_ok=True)
    ideas = load(IDEAS, [])
    state = load(STATE, {"offset": 0, "owner": None})
    res = call("getUpdates", offset=state["offset"], timeout=0, allowed_updates='["message"]')
    changed = False
    for upd in res.get("result", []):
        state["offset"] = upd["update_id"] + 1
        changed = True
        msg = upd.get("message") or {}
        text = (msg.get("text") or "").strip()
        chat = (msg.get("chat") or {}).get("id")
        if not text or chat is None:
            continue
        if state["owner"] is None:
            state["owner"] = chat
            say(chat, "Hi George. This bot is now linked to you only.\n\n"
                      "Send me any blog topic idea as a message and the next scheduled blog post will use it "
                      "before searching for a trending topic.\n\nSend /ideas to see what's waiting.")
            if text.startswith("/"):
                continue
        if chat != state["owner"]:
            continue
        if text.startswith("/start") or text.startswith("/help"):
            say(chat, "Send any topic idea as a message. Send /ideas to list ideas saved so far.")
            continue
        if text.startswith("/ideas"):
            recent = ideas[-10:]
            lines = [f"#{i['id']}: {i['text'][:80]}" for i in recent] or ["No ideas saved yet."]
            say(chat, "Latest ideas (used ones are skipped by the blog writer automatically):\n" + "\n".join(lines))
            continue
        new_id = (max([i["id"] for i in ideas]) + 1) if ideas else 1
        ideas.append({"id": new_id, "text": text,
                      "date": dt.datetime.fromtimestamp(msg.get("date", 0), dt.timezone.utc).isoformat()})
        say(chat, f"Saved idea #{new_id}. It will be used for one of the next blog posts.")
        print("saved idea", new_id)
    if changed:
        IDEAS.write_text(json.dumps(ideas, indent=1, ensure_ascii=False) + "\n")
        STATE.write_text(json.dumps(state, indent=1) + "\n")
    print("ideas total:", len(ideas))


if __name__ == "__main__":
    main()
