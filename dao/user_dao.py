from models.user import User
from utils.db import get_connection, get_current_user_id


def _uid(user_id):
    return user_id or get_current_user_id()


def get_user(user_id: str) -> User | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return User.from_row(dict(row)) if row else None


def find_user(username: str, password: str) -> User | None:
    from utils.security import verify_password
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?", (username.strip(),)
    ).fetchone()
    conn.close()
    if not row:
        return None
    user = User.from_row(dict(row))
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_user(username: str, password_hash: str, name: str = "", email: str = "") -> User:
    conn = get_connection()
    conn.execute(
        "INSERT INTO users (id, password_hash, name, email) VALUES (?, ?, ?, ?)",
        (username.strip(), password_hash, name.strip() or username.strip(), email)
    )
    conn.commit()
    conn.close()
    return User(id=username.strip(), password_hash=password_hash,
                name=name.strip() or username.strip(), email=email)


def exists_user(username: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM users WHERE id = ?", (username.strip(),)).fetchone()
    conn.close()
    return row is not None


def update_user(user_id: str, name: str | None = None, email: str | None = None,
                avatar: str | None = None, password_hash: str | None = None) -> bool:
    conn = get_connection()
    fields = []
    values = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if email is not None:
        fields.append("email = ?")
        values.append(email)
    if avatar is not None:
        fields.append("avatar = ?")
        values.append(avatar)
    if password_hash is not None:
        fields.append("password_hash = ?")
        values.append(password_hash)
    if not fields:
        conn.close()
        return False
    values.append(user_id)
    conn.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True


def get_user_stats(user_id: str) -> dict:
    conn = get_connection()
    task_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ?", (user_id,)
    ).fetchone()['cnt']
    done_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM tasks WHERE user_id = ? AND status = 'done'", (user_id,)
    ).fetchone()['cnt']
    avg_ratio = conn.execute(
        "SELECT AVG(CAST(actual_minutes AS REAL) / NULLIF(estimated_minutes, 0)) as avg "
        "FROM tasks WHERE user_id = ? AND status = 'done' AND actual_minutes > 0",
        (user_id,)
    ).fetchone()['avg']
    conn.close()
    return {
        "task_count": task_count,
        "done_count": done_count,
        "avg_ratio": round(avg_ratio, 2) if avg_ratio else 0,
    }