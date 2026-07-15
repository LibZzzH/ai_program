import json
import re
import secrets
from datetime import datetime, timedelta
from utils.security import hash_password, verify_password
from utils.db import get_connection, get_current_user_id
from models.user import User
from dao import user_dao


_USER_ID_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{2,19}$')


def validate_user_id(user_id: str) -> str | None:
    if not user_id:
        return "用户ID不能为空"
    if not _USER_ID_PATTERN.match(user_id):
        return "用户ID仅支持英文字母、数字、下划线，长度3-20位，且必须以字母开头"
    return None


def validate_password(password: str) -> str | None:
    if not password:
        return "密码不能为空"
    if len(password) < 4:
        return "密码至少需要4个字符"
    if len(password) > 64:
        return "密码不能超过64个字符"
    return None


def register_user(username: str, password: str, name: str = "") -> tuple[bool, str]:
    if not username.strip() or not password.strip():
        return False, "用户名和密码不能为空"
    if len(username.strip()) < 2:
        return False, "用户名至少 2 个字符"
    if len(password) < 4:
        return False, "密码至少 4 个字符"

    if user_dao.exists_user(username):
        return False, "用户名已存在"

    hashed = hash_password(password)
    user_dao.create_user(username, hashed, name)
    return True, "注册成功！"


def login_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    if not username.strip() or not password.strip():
        return False, "请输入用户名和密码", None

    user = user_dao.find_user(username, password)
    if not user:
        return False, "用户不存在或密码错误", None

    return True, "登录成功！", {
        "id": user.id,
        "name": user.name or user.id,
    }


def get_user(user_id: str) -> User | None:
    return user_dao.get_user(user_id)


def change_password(user_id: str, old_password: str, new_password: str) -> tuple[bool, str]:
    err = validate_password(new_password)
    if err:
        return False, err

    user = user_dao.get_user(user_id)
    if not user:
        return False, "用户不存在"

    if not verify_password(old_password, user.password_hash):
        return False, "原密码错误"

    new_hash = hash_password(new_password)
    user_dao.update_user(user_id, password_hash=new_hash)
    return True, "密码修改成功"


def update_profile(user_id: str, name: str | None = None,
                   email: str | None = None, avatar: str | None = None) -> bool:
    return user_dao.update_user(user_id, name=name, email=email, avatar=avatar)


def get_user_stats(user_id: str) -> dict:
    return user_dao.get_user_stats(user_id)


def migrate_default_to_user(target_user_id: str):
    conn = get_connection()
    conn.execute("UPDATE tasks SET user_id = ? WHERE user_id = 'default'", (target_user_id,))
    conn.execute("UPDATE settings SET user_id = ? WHERE user_id = 'default'", (target_user_id,))
    conn.execute("UPDATE calendar_events SET user_id = ? WHERE user_id = 'default'", (target_user_id,))
    conn.commit()
    conn.close()


def create_user(user_id: str, name: str = "", email: str = ""):
    user_dao.create_user(user_id, "", name, email)


def list_users() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def generate_remember_token(user_id: str) -> str:
    token = secrets.token_hex(32)
    expires = (datetime.now() + timedelta(days=3)).isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, user_id) VALUES ('remember_token', ?, ?)",
        (json.dumps({"token": token, "expires": expires}), user_id)
    )
    conn.commit()
    conn.close()
    return token


def validate_remember_token(user_id: str, token: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'remember_token' AND user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        data = json.loads(row["value"])
        if data.get("token") != token:
            return None
        if datetime.fromisoformat(data["expires"]) < datetime.now():
            return None
    except (json.JSONDecodeError, ValueError, KeyError):
        return None
    user = user_dao.get_user(user_id)
    if not user:
        return None
    return {"id": user.id, "name": user.name or user.id}


def clear_remember_token(user_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM settings WHERE key = 'remember_token' AND user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user(user_id: str, name: str | None = None, email: str | None = None):
    user_dao.update_user(user_id, name=name, email=email)


def delete_user(user_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM settings WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM calendar_events WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()