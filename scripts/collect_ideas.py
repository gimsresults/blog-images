"""Collect blog topic ideas from George's Telegram topics group.

Runs in a GitHub Action every ~15 minutes. Reads new messages with the Bot API
(getUpdates) and saves every text message posted in the linked group as an
idea in ideas/ideas.json. The bot stays silent in the group.

The first group the bot sees a message from becomes the linked group (saved in
ideas/state.json); messages from any other chat are ignored. Private messages
to the bot from the person who added it are also accepted as ideas, and
/ideas in a private chat lists what's waiting.

Needs env var TELEGRAM_BOT_TOKEN. In BotFather, privacy mode must be disabled
(/setprivacy -> Disable) or the bot made a group admin, so it sees all messages.
"""
import datetime as dt
import json
import os
import pathlib
import re
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


def split_ideas(text):
    """One idea per line; strips list markers like '1.', '2)', '-', '*', '•'."""
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(\d+[.)]|[-*•–])\s*", "", line).strip()
        if len(line) >= 4:
            out.append(line)
    return out


def add_idea(ideas, text, ts, source):
    if any(i["text"].strip().lower() == text.strip().lower() for i in ideas):
        return None
    new_id = (max(i["id"] for i in ideas) + 1) if ideas else 1
    ideas.append({"id": new_id, "text": text, "source": source,
                  "date": dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()})
    return new_id


def main():
    IDEAS.parent.mkdir(exist_ok=True)
    ideas = load(IDEAS, [])
    state = load(STATE, {"offset": 0, "group": None, "owner": None})
    res = call("getUpdates", offset=state["offset"], timeout=0, allowed_updates='["message"]')
    changed = False
    for upd in res.get("result", []):
        state["offset"] = upd["update_id"] + 1
        changed = True
        msg = upd.get("message") or {}
        chat = msg.get("chat") or {}
        ctype, cid = chat.get("type"), chat.get("id")
        sender = (msg.get("from") or {})
        # group upgraded to supergroup: follow the new id
        if msg.get("migrate_to_chat_id") and cid == state.get("group"):
            state["group"] = msg["migrate_to_chat_id"]
            continue
        if ctype in ("group", "supergroup"):
            if state.get("group") is None:
                state["group"] = cid
                if msg.get("new_chat_members") or msg.get("group_chat_created"):
                    state["owner"] = state.get("owner") or sender.get("id")
                print("linked group", cid, chat.get("title"))
            if cid != state["group"]:
                continue
            if sender.get("is_bot"):
                continue
            # Forum group (topics): only take messages from the ideas topic
            # (e.g. "Blog_ideas"); General, New Leads etc. are ignored so lead
            # details never end up in this public repo.
            if chat.get("is_forum"):
                thread = msg.get("message_thread_id") if msg.get("is_topic_message") else None
                topic = ((msg.get("reply_to_message") or {}).get("forum_topic_created") or {}).get("name", "")
                if thread and "idea" in topic.lower():
                    state["topic"] = thread
                if not thread or thread != state.get("topic"):
                    continue
            text = (msg.get("text") or msg.get("caption") or "").strip()
            if not text or text.startswith("/"):
                continue
            for line in split_ideas(text):
                print("saved idea", add_idea(ideas, line, msg.get("date", 0), "group"))
        elif ctype == "private":
            text = (msg.get("text") or "").strip()
            if state.get("owner") is None:
                state["owner"] = sender.get("id")
            if sender.get("id") != state.get("owner") or not text:
                continue
            if text.startswith("/ideas"):
                recent = ideas[-10:]
                lines = [f"#{i['id']}: {i['text'][:80]}" for i in recent] or ["No ideas saved yet."]
                say(cid, "Latest ideas (the blog writer skips ones already used):\n" + "\n".join(lines))
            elif text.startswith("/"):
                say(cid, "Post topic ideas in your group (or send them here). Send /ideas to see the latest.")
            else:
                ids = [add_idea(ideas, line, msg.get("date", 0), "dm") for line in split_ideas(text)]
                ids = [str(i) for i in ids if i]
                say(cid, f"Saved idea #{', #'.join(ids)}." if ids else "Already saved.")
    if changed:
        IDEAS.write_text(json.dumps(ideas, indent=1, ensure_ascii=False) + "\n")
        STATE.write_text(json.dumps(state, indent=1) + "\n")
    print("ideas total:", len(ideas), "group:", state.get("group"))


if __name__ == "__main__":
    main()
