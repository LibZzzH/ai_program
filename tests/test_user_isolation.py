import utils.db as db
from dao import task_dao


def test_tasks_are_scoped_by_user_id(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO users (id, password_hash, name, email) VALUES (?, '', ?, '')",
            ("alice", "Alice"),
        )
        conn.execute(
            "INSERT INTO users (id, password_hash, name, email) VALUES (?, '', ?, '')",
            ("bob", "Bob"),
        )
        conn.commit()
    finally:
        conn.close()

    task_dao.add_task("work", "alice task", 10, created_date="2026-07-01", user_id="alice")
    task_dao.add_task("work", "bob task", 20, created_date="2026-07-01", user_id="bob")

    alice_tasks = task_dao.get_all_tasks(user_id="alice")
    bob_tasks = task_dao.get_all_tasks(user_id="bob")

    assert [task["description"] for task in alice_tasks] == ["alice task"]
    assert [task["description"] for task in bob_tasks] == ["bob task"]
