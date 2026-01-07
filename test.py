def calculate_percentage(a, b):
    # 将输入值转换为数字类型（整数或浮点数）
    a = float(a)
    b = float(b)
    # 判断哪个数大，哪个数小
    if a < b:
        numerator = a
        denominator = b
    else:
        numerator = b
        denominator = a
    
    # 计算百分比
    percentage = (numerator / denominator) * 100
    return f"{percentage:.2f}%"

# 测试
print(calculate_percentage('7', '5')) # 200.00%
print(calculate_percentage(5, 10)) # 25.00%