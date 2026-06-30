import pymysql


class Sql:

    def __init__(self, host, user, pwd, database):
        # 建立连接
        self.conn = pymysql.connect(host, user, pwd, database)
        self.cursor = self.conn.cursor()
        self.dict = self.conn.cursor(pymysql.cursor.DictCursor)

    # 查询所有数据
    def select_all(self, sql):
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        return result

    # 查询一条数据
    def select_one(self, sql):
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        return result


if __name__ == "__main__":
    db = Sql("test.lemonban.com", "test", "test", "future")
    sql = "select max(MobilePhone) from member"
    res = db.query_all(sql)
    print(*res[0])
