"""
Stoken Advisory — Authentication & User Management
Sessões via cookie, senhas com hash, permissões por role.
"""

import hashlib
import secrets
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Password hashing ─────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = "stoken-advisory-2026"
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return _hash_password(password) == hashed


# ─── User Store ───────────────────────────────────────────────────────────────

ROLES = {
    "admin": {
        "label": "Administrador",
        "permissions": ["view", "edit", "delete", "manage_users", "run_agents", "run_pipeline"]
    },
    "editor": {
        "label": "Editor",
        "permissions": ["view", "edit", "run_agents", "run_pipeline"]
    },
    "viewer": {
        "label": "Visualizador",
        "permissions": ["view"]
    }
}

_users = [
    {
        "id": 1,
        "username": "admin",
        "name": "Administrador",
        "email": "admin@stoken.com.br",
        "role": "admin",
        "password_hash": _hash_password("admin123"),
        "active": True,
        "created_at": "2026-03-01T00:00:00",
    }
]

_sessions = {}  # token → user_id
_next_user_id = 2


# ─── Session Management ──────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = user_id
    logger.info(f"Session created for user #{user_id}")
    return token


def get_session_user(token: str) -> Optional[dict]:
    if not token:
        return None
    user_id = _sessions.get(token)
    if user_id is None:
        return None
    return get_user_by_id(user_id)


def destroy_session(token: str):
    _sessions.pop(token, None)


# ─── User CRUD ────────────────────────────────────────────────────────────────

def authenticate(username: str, password: str) -> Optional[dict]:
    for user in _users:
        if user["username"] == username and user["active"]:
            if verify_password(password, user["password_hash"]):
                return _safe_user(user)
    return None


def get_user_by_id(user_id: int) -> Optional[dict]:
    for user in _users:
        if user["id"] == user_id:
            return _safe_user(user)
    return None


def get_all_users() -> list:
    return [_safe_user(u) for u in _users]


def create_user(data: dict) -> dict:
    global _next_user_id
    user = {
        "id": _next_user_id,
        "username": data["username"],
        "name": data.get("name", data["username"]),
        "email": data.get("email", ""),
        "role": data.get("role", "viewer"),
        "password_hash": _hash_password(data["password"]),
        "active": True,
        "created_at": datetime.now().isoformat(),
    }
    _users.append(user)
    _next_user_id += 1
    logger.info(f"User created: {user['username']} (#{user['id']})")
    return _safe_user(user)


def update_user(user_id: int, data: dict) -> Optional[dict]:
    for user in _users:
        if user["id"] == user_id:
            if "name" in data:
                user["name"] = data["name"]
            if "email" in data:
                user["email"] = data["email"]
            if "role" in data and data["role"] in ROLES:
                user["role"] = data["role"]
            if "active" in data:
                user["active"] = data["active"]
            if "password" in data and data["password"]:
                user["password_hash"] = _hash_password(data["password"])
            logger.info(f"User updated: {user['username']} (#{user_id})")
            return _safe_user(user)
    return None


def delete_user(user_id: int) -> bool:
    global _users
    # Don't delete last admin
    admins = [u for u in _users if u["role"] == "admin" and u["active"]]
    target = next((u for u in _users if u["id"] == user_id), None)
    if target and target["role"] == "admin" and len(admins) <= 1:
        return False
    _users = [u for u in _users if u["id"] != user_id]
    # Clean sessions
    for token, uid in list(_sessions.items()):
        if uid == user_id:
            del _sessions[token]
    logger.info(f"User deleted: #{user_id}")
    return True


def has_permission(user: dict, permission: str) -> bool:
    if not user:
        return False
    role = ROLES.get(user.get("role", "viewer"), ROLES["viewer"])
    return permission in role["permissions"]


def _safe_user(user: dict) -> dict:
    """Return user dict without password hash."""
    return {k: v for k, v in user.items() if k != "password_hash"}
