import json
import os
import uuid
import datetime
from fastapi import HTTPException, Header

USERS_FILE = "users.json"

# Ensure the file exists
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f, indent=4)


def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(data):
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def register_key(plan: str = "free"):
    """Register a new API key for a user (called by PHP or admin)."""
    data = load_users()

    api_key = str(uuid.uuid4())
    now = datetime.datetime.now().isoformat()

    if plan == "free":
        limit = 10
        expiry = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()
    elif plan == "paid":
        limit = None  # unlimited
        expiry = (datetime.datetime.now() + datetime.timedelta(days=365)).isoformat()
    else:
        raise ValueError("Invalid plan type (use 'free' or 'paid')")

    data[api_key] = {
        "plan": plan,
        "limit": limit,
        "usage": 0,
        "created_at": now,
        "expiry": expiry
    }

    save_users(data)
    return api_key


def validate_key(api_key: str = Header(None)):
    """Validate an API key passed in the request header."""
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key in headers")

    data = load_users()

    if api_key not in data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = data[api_key]
    now = datetime.datetime.now()

    # Check expiry
    expiry_date = datetime.datetime.fromisoformat(user["expiry"])
    if now > expiry_date:
        raise HTTPException(status_code=403, detail="API key expired")

    # Check usage limit (for free plan)
    if user["plan"] == "free" and user["usage"] >= user["limit"]:
        raise HTTPException(status_code=403, detail="Monthly usage limit reached (free plan)")

    return user


def increment_usage(api_key: str):
    """Increase the usage count of the API key."""
    data = load_users()

    if api_key not in data:
        return False

    user = data[api_key]
    if user["plan"] == "free":
        user["usage"] += 1
        save_users(data)
    return True


def get_usage_info(api_key: str):
    """Return usage and plan details for a specific API key."""
    data = load_users()

    if api_key not in data:
        raise HTTPException(status_code=401, detail="Invalid API key")

    user = data[api_key]
    remaining = None
    if user["plan"] == "free":
        remaining = max(0, user["limit"] - user["usage"])

    return {
        "plan": user["plan"],
        "limit": user["limit"],
        "usage": user["usage"],
        "remaining": remaining,
        "expiry": user["expiry"]
    }
