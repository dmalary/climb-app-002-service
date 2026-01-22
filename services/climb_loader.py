import sqlite3

def load_climb_from_db(db_path: str, climb_uuid: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            c.*,
            p.image_filename AS base_image_filename
        FROM climbs c
        LEFT JOIN product_sizes_layouts_sets p
            ON p.id = c.product_sizes_layouts_set_id
        WHERE c.uuid = ?
        LIMIT 1
        """,
        (climb_uuid,)
    )

    row = cur.fetchone()
    conn.close()
    if not row:
        return None

    return {k: row[k] for k in row.keys()}
