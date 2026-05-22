from http.server import BaseHTTPRequestHandler
import json
import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        data = json.loads(body)

        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            text = data["message"].get("text", "")

            requests.post(
                f"{API_URL}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": f"You said: {text}"
                }
            )

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")