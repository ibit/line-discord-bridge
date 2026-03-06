import os, json, hashlib, hmac, base64, requests
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

LINE_SECRET     = os.getenv("LINE_CHANNEL_SECRET")
LINE_TOKEN      = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_GROUP_ID   = os.getenv("LINE_GROUP_ID")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

app = FastAPI()

def verify_signature(body: bytes, sig: str) -> bool:
    h = hmac.new(LINE_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(h).decode(), sig)

def get_display_name(user_id: str) -> str:
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    # グループメンバーのプロフィール取得
    r = requests.get(
        f"https://api.line.me/v2/bot/group/{LINE_GROUP_ID}/member/{user_id}",
        headers=headers
    )
    return r.json().get("displayName", "Unknown") if r.ok else "Unknown"

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-Line-Signature", "")
    if not verify_signature(body, sig):
        raise HTTPException(status_code=403)

    for event in json.loads(body).get("events", []):
        source = event.get("source", {})

        # グループIDをまだ取得していない場合はログに出す
        if source.get("type") == "group" and not LINE_GROUP_ID:
            print(f"[GROUP ID] {source.get('groupId')}")

        # テキストメッセージだけ処理
        if event.get("type") == "message" and event["message"]["type"] == "text":
            name = get_display_name(source.get("userId", ""))
            text = event["message"]["text"]
            requests.post(DISCORD_WEBHOOK, json={
                "username": f"[LINE] {name}",
                "content": text
            })

    return {"status": "ok"}