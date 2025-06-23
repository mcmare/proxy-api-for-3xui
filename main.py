from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from urllib.parse import urlencode
import json
import uvicorn
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime, timedelta

# Загружаем переменные из .env
load_dotenv()

app = FastAPI()

# Конфигурация целевого сервера 3X-UI
TARGET_SERVER = os.getenv("TARGET_SERVER")

# Учетные данные из .env
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# Проверяем наличие учетных данных
if not USERNAME or not PASSWORD:
    raise ValueError("USERNAME and PASSWORD must be set in .env file")

# Конфигурация по умолчанию для добавления клиента
DEFAULT_INBOUND_ID = 1  # Можно изменить, если нужен другой inbound
DEFAULT_FLOW = "xtls-rprx-vision"  # Протокол для клиента

# Параметры для строки подключения VLESS
VLESS_CONFIG = {
    "host": "example.com", #Поменять на свой хост
    "port": "443",
    "type": "tcp",
    "security": "reality",
    "pbk": "98VanBnRnzoHAN7AiD0_32Fp691pBSUQ4JFaSEtfsGI",
    "fp": "chrome",
    "sni": "yahoo.com",
    "sid": "8d8a5508",
    "spx": "%2F",
    "flow": "xtls-rprx-vision"
}

# Модель для входящих данных (только email)
class AddClientPayload(BaseModel):
    email: str

async def perform_login(client: httpx.AsyncClient):
    """Выполняет запрос логина и возвращает cookie сессии"""
    login_url = f"{TARGET_SERVER}/login"
    login_data_encoded = urlencode({"username": USERNAME, "password": PASSWORD})
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "curl/7.88.1",
        "Referer": f"{TARGET_SERVER}/",
        "Origin": TARGET_SERVER
    }

    try:
        response = await client.post(login_url, content=login_data_encoded, headers=headers)
        print(f"Login response: {response.status_code} - {response.text} - Cookies: {response.cookies}")  # Отладка
        response.raise_for_status()
        if not client.cookies.get("3x-ui"):
            raise HTTPException(status_code=403, detail="Login failed: No 3x-ui cookie received")
        return response
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Login failed: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

async def add_client(client: httpx.AsyncClient, email: str):
    """Добавляет клиента в inbound и возвращает строку подключения VLESS"""
    add_client_url = f"{TARGET_SERVER}/panel/inbound/addClient"

    # Генерируем UUID для клиента
    client_id = str(uuid.uuid4())

    # Рассчитываем срок действия (30 дней от текущей даты)
    expiry_time = int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)

    # Формируем settings
    settings = {
        "clients": [
            {
                "id": client_id,
                "email": email,
                "flow": DEFAULT_FLOW,
                "enable": True,
                "expiryTime": expiry_time
            }
        ]
    }

    data = {
        "id": DEFAULT_INBOUND_ID,
        "settings": json.dumps(settings)
    }
    data_encoded = urlencode(data)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "curl/7.88.1",
        "Referer": f"{TARGET_SERVER}/",
        "Origin": TARGET_SERVER
    }

    try:
        print(f"Sending addClient request with cookies: {client.cookies}")  # Отладка
        response = await client.post(add_client_url, content=data_encoded, headers=headers)
        print(f"Add Client response: {response.status_code} - {response.text}")  # Отладка
        response.raise_for_status()

        # Формируем строку подключения VLESS
        vless_string = (
            f"vless://{client_id}@{VLESS_CONFIG['host']}:{VLESS_CONFIG['port']}?"
            f"type={VLESS_CONFIG['type']}&security={VLESS_CONFIG['security']}&"
            f"pbk={VLESS_CONFIG['pbk']}&fp={VLESS_CONFIG['fp']}&sni={VLESS_CONFIG['sni']}&"
            f"sid={VLESS_CONFIG['sid']}&spx={VLESS_CONFIG['spx']}&flow={VLESS_CONFIG['flow']}#"
            f"McMare-VLESS-{email}"
        )
        return {"vless": vless_string}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Add client failed: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add client error: {str(e)}")

@app.post("/proxy/add-client")
async def proxy_add_client(payload: AddClientPayload):
    async with httpx.AsyncClient(verify=False) as client:
        # Выполняем логин
        await perform_login(client)

        # Выполняем запрос на добавление клиента
        response = await add_client(client, payload.email)

        return response


async def add_test_client(client: httpx.AsyncClient, email: str):
    """Добавляет клиента в inbound и возвращает строку подключения VLESS"""
    add_client_url = f"{TARGET_SERVER}/panel/inbound/addClient"

    # Генерируем UUID для клиента
    client_id = str(uuid.uuid4())

    # Рассчитываем срок действия (30 дней от текущей даты)
    expiry_time = int((datetime.utcnow() + timedelta(days=1)).timestamp() * 1000)

    # Формируем settings
    settings = {
        "clients": [
            {
                "id": client_id,
                "email": email,
                "flow": DEFAULT_FLOW,
                "enable": True,
                "expiryTime": expiry_time
            }
        ]
    }

    data = {
        "id": DEFAULT_INBOUND_ID,
        "settings": json.dumps(settings)
    }
    data_encoded = urlencode(data)
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "curl/7.88.1",
        "Referer": f"{TARGET_SERVER}/",
        "Origin": TARGET_SERVER
    }

    try:
        print(f"Sending addClient request with cookies: {client.cookies}")  # Отладка
        response = await client.post(add_client_url, content=data_encoded, headers=headers)
        print(f"Add Client response: {response.status_code} - {response.text}")  # Отладка
        response.raise_for_status()

        # Формируем строку подключения VLESS
        vless_string = (
            f"vless://{client_id}@{VLESS_CONFIG['host']}:{VLESS_CONFIG['port']}?"
            f"type={VLESS_CONFIG['type']}&security={VLESS_CONFIG['security']}&"
            f"pbk={VLESS_CONFIG['pbk']}&fp={VLESS_CONFIG['fp']}&sni={VLESS_CONFIG['sni']}&"
            f"sid={VLESS_CONFIG['sid']}&spx={VLESS_CONFIG['spx']}&flow={VLESS_CONFIG['flow']}#"
            f"McMare-VLESS-{email}"
        )
        return {"vless": vless_string}
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Add client failed: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Add client error: {str(e)}")

@app.post("/proxy/add-test-client")
async def proxy_add_test_client(payload: AddClientPayload):
    async with httpx.AsyncClient(verify=False) as client:
        # Выполняем логин
        await perform_login(client)

        # Выполняем запрос на добавление клиента
        response = await add_test_client(client, payload.email)

        return response

@app.get("/")
def proxy():
    print("Proxy API for 3XUI. https://github.com/mcmare/proxy-api-for-3xui")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=22548)
