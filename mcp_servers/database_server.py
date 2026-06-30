import pymysql
from contextlib import contextmanager


class DatabaseMCPClient:
    """
    数据库 MCP 客户端
    暴露的能力:
    - query: 执行 SQL 查询
    - get_table_schema: 获取表结构
    - compare_data: 数据比对
    """

    def __init__(self, host=None, user=None, password=None, database=None, port=3306):
        self.config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "charset": "utf8mbdb",
        }
        self._connection = None

    def _get_connection(self):
        if self._connection is None or not self._connection.open:
            self._connection = pymysql.connect(**self.config)
        return self._connection

    @contextmanager
    def _cursor(self, dict_cursor=True):
        conn = self._get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor if dict_cursor else pymysql.cursors.Cursor)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def query(self, sql, params=None):
        """
        执行 SQL 查询并返回结果
        :param sql: SQL 语句
        :param params: 参数化查询参数
        :return: 查询结果列表
        """
        with self._cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def query_one(self, sql, params=None):
        """
        执行 SQL 查询并返回单条结果
        """
        with self._cursor(dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def execute(self, sql, params=None):
        """
        执行 INSERT/UPDATE/DELETE
        :return: 影响行数
        """
        with self._cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    def get_table_schema(self, table_name):
        """
        获取表结构信息
        :param table_name: 表名
        :return: 字段信息列表
        """
        sql = """
            SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY,
                   COLUMN_DEFAULT, EXTRA, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """
        return self.query(sql, [self.config["database"], table_name])

    def get_table_names(self):
        """
        获取当前数据库所有表名
        """
        sql = """
            SELECT TABLE_NAME, TABLE_COMMENT
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s
        """
        return self.query(sql, [self.config["database"]])

    def compare_data(self, table_name, conditions, expected_data):
        """
        数据比对: 查询数据库记录并与期望数据对比
        :param table_name: 表名
        :param conditions: WHERE 条件字典 {"column": "value"}
        :param expected_data: 期望数据字典 {"column": "expected_value"}
        :return: 比对结果
        """
        where_clause = " AND ".join([f"`{k}` = %s" for k in conditions.keys()])
        sql = f"SELECT * FROM `{table_name}` WHERE {where_clause}"
        actual = self.query_one(sql, list(conditions.values()))

        if actual is None:
            return {"match": False, "error": "record_not_found", "detail": conditions}

        mismatches = []
        for field, expected_value in expected_data.items():
            actual_value = actual.get(field)
            if str(actual_value) != str(expected_value):
                mismatches.append({
                    "field": field,
                    "expected": expected_value,
                    "actual": actual_value,
                })

        return {
            "match": len(mismatches) == 0,
            "mismatches": mismatches,
            "actual_record": actual,
        }

    def close(self):
        if self._connection and self._connection.open:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
