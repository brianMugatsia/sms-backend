import requests

BASE_URL = "http://127.0.0.1:8000"  # FastAPI backend
USERNAME = "brian"
EMAIL = "brian@example.com"
PASSWORD = "brian123"

def register():
    user = {
        "username": USERNAME,
        "email": EMAIL,
        "password": PASSWORD,
        "role": "user"
    }
    response = requests.post(f"{BASE_URL}/api/users/register", json=user)
    print("REGISTER STATUS:", response.status_code)
    print(response.json())

def login():
    response = requests.post(
        f"{BASE_URL}/api/users/login",
        data={"username": USERNAME, "password": PASSWORD}
    )
    print("LOGIN STATUS:", response.status_code)
    if response.status_code != 200:
        print(response.text)
        exit()
    token = response.json()["access_token"]
    print("TOKEN:", token[:50], "...")
    return token

def send_sms(token):
    sms = {
        "sender": "+254792117538",
        "message": "Hello from test.py",
        "device_id": "android"
    }
    response = requests.post(
        f"{BASE_URL}/api/sms/forward",
        json=sms,
        headers={"Authorization": f"Bearer {token}"}
    )
    print("SMS STATUS:", response.status_code)
    print(response.json())

def list_sms(token):
    response = requests.get(
        f"{BASE_URL}/api/sms/list",
        headers={"Authorization": f"Bearer {token}"}
    )
    print("LIST STATUS:", response.status_code)
    print(response.json())

if __name__ == "__main__":
    register()
    token = login()
    send_sms(token)
    list_sms(token)
