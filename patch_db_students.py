import sqlite3

db_path = "corebox.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

statements = [
    # New flags so code can query students.is_active / is_anonymized
    "ALTER TABLE students ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1",
    "ALTER TABLE students ADD COLUMN is_anonymized BOOLEAN NOT NULL DEFAULT 0",
    # Anonymization metadata (nullable is fine)
    "ALTER TABLE students ADD COLUMN anonymized_at DATETIME NULL",
    "ALTER TABLE students ADD COLUMN anonymized_by_id INTEGER NULL",
]

for sql in statements:
    try:
        cur.execute(sql)
        print("OK:", sql)
    except sqlite3.OperationalError as e:
        # If the column already exists, just skip it
        print("SKIP:", sql, "->", e)

conn.commit()
conn.close()
print("Done.")
