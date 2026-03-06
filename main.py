import os, json, hashlib, hmac, base64, requests
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

LINE_SECRET     = os.getenv("LINE_CHANNEL_SECRET", "").strip()
LINE_TOKEN      = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
LINE_GROUP_ID   = os.getenv("LINE_GROUP_ID", "").strip()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

app = FastAPI()

# 起動時に変数が読めているか確認
print(f"[DEBUG] SECRET={'OK' if LINE_SECRET else 'NG'}, TOKEN={'OK' if LINE_TOKEN else 'NG'}, WEBHOOK={'OK' if DISCORD_WEBHOOK else 'NG'}")

def verify_signature(body: bytes, sig: str) -> bool:
    h = hmac.new(LINE_SECRET.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(h).decode(), sig)

def get_display_name(user_id: str) -> str:
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    r = requests.get(
        f"https://api.line.me/v2/bot/group/{LINE_GROUP_ID}/member/{user_id}",
        headers=headers
    )
    return r.json().get("displayName", "Unknown") if r.ok else "Unknown"

@app.post("/webhook")
async def webhook(request: Request):
    try:
        body = await request.body()
        sig  = request.headers.get("X-Line-Signature", "")
        
        print(f"[DEBUG] Webhook received, sig_len={len(sig)}, body_len={len(body)}")
        
        if not verify_signature(body, sig):
            print("[ERROR] 署名検証失敗")
            raise HTTPException(status_code=403)

        for event in json.loads(body).get("events", []):
            source = event.get("source", {})
            if source.get("type") == "group" and not LINE_GROUP_ID:
                print(f"[GROUP ID] {source.get('groupId')}")
            if event.get("type") == "message" and event["message"]["type"] == "text":
                name = get_display_name(source.get("userId", ""))
                text = event["message"]["text"]
                requests.post(DISCORD_WEBHOOK, json={
                    "username": f"[LINE] {name}",
                    "content": text
                })

        return {"status": "ok"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[EXCEPTION] {type(e).__name__}: {e}")
        raise HTTPException(status_code=400, detail=str(e))