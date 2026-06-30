import calendar
import datetime
import time
from datetime import timedelta

# 当前时间戳
now_ts = int(time.time() * 1000)
# 今天日期返回datetime
# now = datetime.datetime.now().timestamp()
# 返回datetime格式：
now = datetime.datetime.now().date()
now = datetime.date.today()

# 获取本周第一天和最后一天
this_week_start = now - timedelta(days=now.weekday())
this_week_end = now + timedelta(days=6 - now.weekday())

# 获取上周第一天和最后一天
last_week_start = now - timedelta(days=now.weekday() + 7)
last_week_end = now - timedelta(days=now.weekday() + 1)

# 获取本月第一天和最后一天
this_month_start = datetime.datetime(now.year, now.month, 1)
this_month_end = datetime.datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])

# 获取本年第一天和最后一天
this_year_start = datetime.datetime(now.year, 1, 1)
this_year_end = datetime.datetime(now.year + 1, 1, 1) - timedelta(days=1)

# 获取去年第一天和最后一天
last_year_end = this_year_start - timedelta(days=1)
last_year_start = datetime.datetime(last_year_end.year, 1, 1)


# 转换时间戳
def get_ts(date):
    try:
        return int(date.timestamp() * 1000)
    except:
        tmp = str(date) + " 00:00:00"
        ts = time.strptime(str(tmp), "%Y-%m-%d %H:%M:%S")
        return int(time.mktime(ts) * 1000)


if __name__ == "__main__":
    print(now_ts)
    print(time.ctime())
