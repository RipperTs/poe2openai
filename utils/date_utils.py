from datetime import datetime, timedelta, date


def get_week_boundaries(date_str):
    """
    返回给定日期所在周的开始日期和结束日期（周一和周日）。

    参数:
    - date_str: 日期字符串，格式为 'YYYY-MM-DD'

    返回:
    - 一个元组，包含周的开始日期和结束日期的字符串
    """
    # 将输入的字符串转换为日期对象
    given_date = datetime.strptime(date_str, '%Y-%m-%d')

    # 计算周的开始日期（周一）
    start_date = given_date - timedelta(days=given_date.weekday())

    # 计算周的结束日期（周日）
    end_date = start_date + timedelta(days=6)

    return start_date, end_date


# 自定义日期序列化函数
def date_serializer(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} is not JSON serializable")


if __name__ == '__main__':
    print(get_week_boundaries('2021-01-01'))
