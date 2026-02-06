import requests
import os
import json

APP_ID = os.environ.get["APPLICATION_ID"]
BOT_TOKEN = os.environ.get["DISCORD_BOT_TOKEN"]

url = f"https://discord.com/api/v10/applications/{APP_ID}/commands"

headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

commands = [
    {
        "name": "m",
        "description": "memebot 명령어",
        "options": [
            {
                "name": "sc",
                "description": "스커프 밈 생성",
                "type": 1
            },
            {
                "name": "clip",
                "description": "하이라이트 생성",
                "type": 1
            }
        ]
    }
]

res = requests.put(url, headers=headers, json=commands)

print(res.status_code)
print(res.text)
