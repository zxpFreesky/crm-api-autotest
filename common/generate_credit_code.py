import random


def generate_uscc():
    """生成符合规则的18位统一社会信用代码"""
    # 可用字符集（不含 I, O, S, V, Z），与JS完全一致
    charset = "0123456789ABCDEFGHJKLMNPQRTUWXY"

    # 权重因子（前17位用于计算校验码）
    weights = [1, 3, 9, 27, 19, 26, 16, 17,
               20, 29, 25, 13, 8, 24, 10, 30, 28]

    # 随机生成前17位：Python用random.choice替代JS的Math.random+索引
    code17 = ""
    for _ in range(17):
        # 从字符集中随机选一个字符，等价于JS的 charset[Math.floor(Math.random() * charset.length)]
        code17 += random.choice(charset)

    # 计算加权和：逻辑与JS完全一致
    sum_total = 0  # 避免与Python内置sum函数重名，改用sum_total
    for i in range(17):
        char = code17[i]
        # 找到字符在字符集中的索引值
        value = charset.index(char)
        sum_total += value * weights[i]

    # 计算校验码索引
    check_index = 31 - (sum_total % 31)
    if check_index == 31:
        check_index = 0
    check_code = charset[check_index]

    # 拼接完整的18位统一社会信用代码并返回
    return code17 + check_code


def generate_codes(num=1):
    """
    生成多个统一社会信用代码（替代JS的DOM操作逻辑）
    :param num: 要生成的代码数量，默认1个
    :return: 包含生成代码的列表
    """
    codes_list = []
    for _ in range(num):
        uscc = generate_uscc()
        codes_list.append(uscc)
        # 模拟JS的页面输出，这里打印到控制台

    return codes_list[0]


# 测试调用：生成5个统一社会信用代码
if __name__ == "__main__":
    generated_codes = generate_codes()
    print("\n所有生成的代码列表：", generated_codes)