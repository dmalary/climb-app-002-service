import sqlite3

def build_local_board_db(board):
    database_path = f"{board}.db"
    conn = sqlite3.connect(database_path)
    cur = conn.cursor()

    # Create climbs table if it doesn't exist
    cur.execute("""
      CREATE TABLE IF NOT EXISTS climbs (
        uuid TEXT PRIMARY KEY,
        name TEXT,
        angle INTEGER,
        difficulty INTEGER
      )
    """)

    # Optionally: you can prefill sample data or leave empty
    # cur.execute("INSERT INTO climbs (uuid, name, angle, difficulty) VALUES (?, ?, ?, ?)",
    #            ("sample-uuid", "Sample Climb", 30, 5))

    conn.commit()
    conn.close()
    return database_path
