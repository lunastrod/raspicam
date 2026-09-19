import sqlite3

FILENAME = "users.db"

import sqlite3

FILENAME = "users.db"  # or wherever you want your DB file to live

class UserDB:
    def __init__(self):
        pass
        # self.create_table()

    def connect(self):
        """Open a new connection for each operation."""
        conn = sqlite3.connect(FILENAME)
        cursor = conn.cursor()
        return conn, cursor

    def create_table(self):
        try:
            conn, cursor = self.connect()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    is_admin INTEGER DEFAULT 0,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during table creation: {e}")
        finally:
            conn.close()

    def add_user(self, user_id: int, username: str, is_admin: int = 0) -> bool:
        """Adds a new user to the database."""
        try:
            conn, cursor = self.connect()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, is_admin) VALUES (?, ?, ?)",
                (user_id, username, is_admin)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Database error while adding user {user_id}: {e}")
            return False
        finally:
            conn.close()

    def get_user(self, user_id: int):
        """Retrieves a single user's record."""
        conn, cursor = self.connect()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def get_all_users(self):
        """Retrieves all users."""
        conn, cursor = self.connect()
        cursor.execute("SELECT user_id, username, is_admin, added_at FROM users")
        users = cursor.fetchall()
        conn.close()
        return users

    def is_user_admin(self, user_id: int) -> bool:
        """Checks if a user is an admin."""
        user = self.get_user(user_id)
        return user is not None and user[2] == 1  # is_admin is now the 3rd field

    def get_admin(self):
        """Returns (user_id, username) of the current admin, or None."""
        conn, cursor = self.connect()
        cursor.execute("SELECT user_id, username FROM users WHERE is_admin = 1 LIMIT 1")
        admin = cursor.fetchone()
        conn.close()
        return admin

    def delete_user(self, user_id: int) -> bool:
        """Deletes a user from the database."""
        conn, cursor = self.connect()
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0



if __name__ == "__main__":
    db = UserDB()
    db.create_table()
    print(db.get_admin())
    print(db.get_all_users())