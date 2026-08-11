from contextlib import contextmanager
import unittest

from zworkforce.db_base import DatabaseBase


class _Result:
    def fetchone(self):
        return (1,)


class _RecordingConnection:
    def __init__(self, fail_schema_meta=False):
        self.statements = []
        self.fail_schema_meta = fail_schema_meta

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if self.fail_schema_meta and sql.startswith("INSERT INTO schema_meta"):
            raise RuntimeError("forced schema failure")
        return _Result()

    def executescript(self, script):
        self.statements.append(("SCRIPT", script))
        return _Result()


class PostgresInitializationTransactionTests(unittest.TestCase):
    def database_with(self, connection):
        database = object.__new__(DatabaseBase)
        database.backend_kind = "postgres"
        database.default_tenant = "test"
        database.ensure_tenant = lambda *_args: {}
        database._ensure_v4_schema = lambda c: c.execute("V4 DDL")

        @contextmanager
        def use_connection():
            yield connection

        database.connection = use_connection
        return database

    def test_postgres_schema_ddl_uses_transaction_scoped_advisory_lock(self):
        connection = _RecordingConnection()
        self.database_with(connection).initialize()

        sql = [statement for statement, _params in connection.statements]
        self.assertEqual(sql[0], "BEGIN")
        self.assertEqual(sql[1], "SELECT pg_advisory_xact_lock(?)")
        self.assertEqual(sql[-1], "COMMIT")
        self.assertNotIn("SELECT pg_advisory_lock(?)", sql)
        self.assertNotIn("SELECT pg_advisory_unlock(?)", sql)

    def test_postgres_schema_failure_rolls_back_transaction(self):
        connection = _RecordingConnection(fail_schema_meta=True)

        with self.assertRaisesRegex(RuntimeError, "forced schema failure"):
            self.database_with(connection).initialize()

        sql = [statement for statement, _params in connection.statements]
        self.assertEqual(sql[-1], "ROLLBACK")
        self.assertNotIn("COMMIT", sql)
        self.assertNotIn("SELECT pg_advisory_unlock(?)", sql)


if __name__ == "__main__":
    unittest.main()
