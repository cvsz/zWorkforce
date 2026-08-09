import unittest

from zworkforce.db_backend import CompatRow, postgres_schema, postgres_sql


class BackendTests(unittest.TestCase):
    def test_qmark_and_transactions(self):
        self.assertEqual(postgres_sql("BEGIN IMMEDIATE"), "BEGIN")
        self.assertEqual(postgres_sql("SELECT * FROM x WHERE a=? AND b='?'"), "SELECT * FROM x WHERE a=%s AND b='?'")

    def test_insert_or_ignore(self):
        sql = postgres_sql("INSERT OR IGNORE INTO x(a) VALUES(?)")
        self.assertIn("INSERT INTO x", sql)
        self.assertIn("ON CONFLICT DO NOTHING", sql)

    def test_schema_autoincrement(self):
        self.assertIn("BIGSERIAL PRIMARY KEY", postgres_schema("id INTEGER PRIMARY KEY AUTOINCREMENT"))

    def test_compat_row(self):
        row = CompatRow(("a","b"), (1,2))
        self.assertEqual(row[0], 1)
        self.assertEqual(row["b"], 2)
        self.assertEqual(dict(row), {"a":1,"b":2})


if __name__ == "__main__":
    unittest.main()
