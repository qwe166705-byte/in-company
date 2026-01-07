import json
import socket
import os
from flask import Flask, request, render_template, current_app, session, redirect, url_for, g, jsonify, send_file
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
import math
import re
import urllib.parse

app = Flask(__name__)
CORS(app)  # 允许所有来源的请求
# 配置服务器地址
app.config['SERVER_URL'] = 'http://10.1.2.164:1111'  # 配置服务器地址
app.secret_key = 'sf.iot.key'

CORS(app)  # 允许所有来源的跨域请求，生产环境中建议指定具体来源

# 计算两个数值或者字符串类型的数值的百分比
def calculate_percentage(a, b, is_change=True):
    # 将输入值转换为数字类型（整数或浮点数）
    a = float(a)
    b = float(b)
    numerator = a
    denominator = b
    if int(a) == 0 or int(b)==0:
        return f"0.0%"
    # 判断哪个数大，哪个数小
    if is_change and a > b:
        numerator = b
        denominator = a

    # 计算百分比
    percentage = (numerator / denominator) * 100
    # 判断小数位数并格式化
    if percentage.is_integer():  # 如果结果是整数
        return f"{int(percentage)}%"  # 返回整数部分，不显示小数
    else:
        return f"{percentage:.2f}%"  # 默认保留两位小数


# 发送API信息
def get_data_from_server(route, data=None, method='GET'):
    """从服务器获取数据"""
    server_url = current_app.config['SERVER_URL']
    url = f"{server_url}/{route}"
    if method == 'GET':  # 如果是GET请求，将data作为参数传递给url
        response = requests.get(url=url, params=data)
    elif method == 'POST':  # 如果是POST请求，将data作为请求体传递给服务器
        response = requests.post(url=url, json=data)
    elif method == 'PUT':  # 如果是PUT请求，将data作为请求体传递给服务器
        response = requests.put(url=url, json=data)
    elif method == 'DELETE':  # 如果是DELETE请求，将data作为请求体传递给服务器
        response = requests.delete(url=url, json=data)
    else:
        return None
    # print('服务器返回的数据',response.json())
    if response.status_code == 200:  # 如果服务器返回的状态码是200，则表示请求成功
        return response.json()  # 返回服务器返回的数据
    else:
        return {'error': '服务器连接失败','message': '服务器连接失败'}  # 返回错误信息


# 将一部字典的键全部转小写
def convert_keys_to_lowercase(d):
    """递归地将字典的所有键转换为小写"""
    if isinstance(d, dict):
        return {k.lower(): convert_keys_to_lowercase(v) if isinstance(v, (dict, list)) else v for k, v in d.items()}
    elif isinstance(d, list):
        return [convert_keys_to_lowercase(item) if isinstance(item, (dict, list)) else item for item in d]
    else:
        return d


# 格式化时间为 'YYYY-MM-DD HH:MM:SS'，避免带 T
def format_time(time_str):
    try:
        # 第一步：将 'T' 替换为空格，确保时间格式为 'YYYY-MM-DD HH:MM:SS'
        time_str = time_str.replace('T', ' ')
        # 第二步：检查时间部分是否包含秒数（例如 'HH:MM'），如果没有，则补充 ':00'
        if len(time_str.split(' ')[1]) == 5:  # 'HH:MM' 格式
            time_str += ':00'
        return time_str
    except ValueError:
        return time_str  # 如果格式不正确，返回原始字符串


# 在每次请求之前执行做处理
@app.before_request
def check_login():  # 检查用户是否登录
    # 排除静态文件路径
    if request.path.startswith('/static/'):
        return
    if request.path.startswith('/production_records') or '51k' in request.path:
        return

    if 'username' in session:  # 如果session中有用户信息
        g.user = session['username']  # 将用户名存储到g对象中
        g.authority = session['username'].get('AUTHORITY', None)  # 获取用户权限
    else:
        g.user = None
        g.authority = None
        if not request.path.startswith('/login'):  # 不需要检查的页面
            return redirect(url_for('login'))  # 如果没有登录信息，重定向到登录页面


# 捕获 404 错误并渲染自定义的 404 页面
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  # 获取表单中的用户名和密码
        password = request.form['password']  # 获取表单中的用户名和密码
        result = get_data_from_server('check_user_info', data={'user': username, 'password': password},
                                      method='POST')  # 调用get_data_from_server函数，将用户名和密码作为参数传递给服务器
        if not result:
            error_message = "用户名和密码不能为空"  # 如果服务器返回的结果为空，则表示服务器连接失败
            return render_template('login.html', error=True, error_message=error_message)  # 如果服务器返回的结果为空，则表示服务器连接失败
        if result['status'] == 'success':  # 如果服务器返回的结果是success，则表示验证通过
            print('验证通过', result['message'])  # 验证通过，将用户名存储在session中
            # 验证通过，将用户名存储在session中
            session['username'] = result['message']  # 验证通过，将用户名存储在session中
            return redirect(url_for('index'))  # 重定向到主页
        else:
            print('验证失败', result['message'])  # 验证失败，将错误信息存储在session中
            return render_template('login.html', error=True, error_message=result['message'])  # 验证失败，将错误信息存储在session中
    return render_template('login.html')


# 注销页面
@app.route('/logout')
def logout():
    # 清除用户的 session 信息
    session.pop('username', None)  # 删除 session 中的 'username'
    return redirect(url_for('login'))  # 重定向到登录页面


# 网站首页
@app.route('/index', methods=['GET'])
def index():
    data = {}
    date_time = get_data_from_server('sync_time', method='GET')
    date_time = datetime.strptime(date_time['server_time'], '%Y-%m-%d %H:%M:%S')
    machine_count = get_data_from_server('select', data={'query': 'SELECT COUNT(*) FROM machine_info'},
                                         method='POST')  # 获取机器数量
    now_time = (date_time - timedelta(minutes=1)).strftime('%Y/%m/%d %H:%M:%S')  # 获取服务器一分钟前的时间
    machine_online_count = get_data_from_server('select', data={
        'query': 'SELECT COUNT(*) FROM machine_info WHERE LINK_STATUS IS NOT NULL AND LINK_STATUS > %s',
        'params': [now_time]}, method='POST')  # 获取在线机器数量
    cmd_65_upload_count = get_data_from_server('select', data={
        'query': 'SELECT COUNT(*) FROM machine_info WHERE IS_65_UPLOAD = "True"'}, method='POST')  # 获取65上报机器数量
    camera_count = get_data_from_server('select', data={'query': 'SELECT COUNT(*) FROM camera_info'},
                                        method='POST')  # 获取摄像头数量
    camera_online_count = get_data_from_server('select', data={
        'query': 'SELECT COUNT(*) FROM camera_info WHERE LINK_STATUS IS NOT NULL AND LINK_STATUS > %s',
        'params': [now_time]}, method='POST')  # 获取在线摄像头数量
    work_order_count = get_data_from_server('select', data={'query': 'SELECT COUNT(*) FROM work_order_info'},
                                            method='POST')  # 获取工单数量
    param_count = get_data_from_server('select', data={'query': 'SELECT COUNT(*) FROM param_info'},
                                       method='POST')  # 获取参数数量
    user_count = get_data_from_server('select', data={'query': 'SELECT COUNT(*) FROM user_info'},
                                      method='POST')  # 获取用户数量
    data = {'machine_count': machine_count['data'][0]['COUNT(*)'],
            'machine_online_count': machine_online_count['data'][0]['COUNT(*)'],
            'cmd_65_upload_count': cmd_65_upload_count['data'][0]['COUNT(*)'],
            'camera_count': camera_count['data'][0]['COUNT(*)'],
            'camera_online_count': camera_online_count['data'][0]['COUNT(*)'],
            'work_order_count': work_order_count['data'][0]['COUNT(*)'],
            'param_count': param_count['data'][0]['COUNT(*)'], "user_count": user_count['data'][0]['COUNT(*)']}
    machine_count_sum = 800
    machine_sum_rate = calculate_percentage(machine_online_count['data'][0]['COUNT(*)'], machine_count_sum)
    machine_online_rate = calculate_percentage(machine_online_count['data'][0]['COUNT(*)'],
                                               machine_count['data'][0]['COUNT(*)'])
    camera_online_rate = calculate_percentage(camera_online_count['data'][0]['COUNT(*)'],
                                              camera_count['data'][0]['COUNT(*)'])
    return render_template('index.html', data=data, machine_online_rate=machine_online_rate,
                           camera_online_rate=camera_online_rate, machine_sum_rate=machine_sum_rate,
                           machine_count_sum=machine_count_sum)


# 机台信息页面
@app.route('/machine_info', methods=['GET', 'POST'])
def machine_info():
    machine_info = None
    server_url = current_app.config['SERVER_URL']

    # 获取POST请求的表单数据
    machine_name = request.form.get('machine_name', '').strip()  # 默认空字符串
    machine_pm = request.form.get('machine_pm', '').strip()  # 默认空字符串
    query_params = {
        'machine_name': machine_name,
        'machine_pm': machine_pm
    }

    # 获取当前页码，默认为1
    page = int(request.args.get('page', 1))  # 从URL参数获取page，默认为第1页
    per_page = 15  # 每页显示15条记录

    # SQL查询初始化
    query = 'SELECT * FROM machine_info WHERE 1=1'
    params = []

    if machine_pm:
        query += " AND machine_pm LIKE %s"
        params.append(f"%{machine_pm}%")
    if machine_name:
        query += " AND machine_name LIKE %s"
        params.append(f"%{machine_name}%")

    # 获取数据总条数
    count_query = 'SELECT COUNT(*) FROM machine_info WHERE 1=1'
    count_params = params[:]
    if machine_pm:
        count_query += " AND machine_pm LIKE %s"
    if machine_name:
        count_query += " AND machine_name LIKE %s"

    # 获取总记录数
    count_result = get_data_from_server('select', data={'query': count_query, 'params': count_params}, method='POST')
    total_count = count_result['data'][0]['COUNT(*)'] if count_result else 0
    total_pages = (total_count // per_page) + (1 if total_count % per_page > 0 else 0)

    # 获取分页数据
    query += " LIMIT %s OFFSET %s"
    params.append(per_page)
    params.append((page - 1) * per_page)

    # 执行查询
    result = get_data_from_server('select', data={'query': query, 'params': params}, method='POST')
    if result and 'error' not in result:
        machine_info = result['data']
        # 获取同步时间
        date_time = get_data_from_server('sync_time', method='GET')
        if date_time:
            date_time = datetime.strptime(date_time['server_time'], '%Y-%m-%d %H:%M:%S')
            for machine in machine_info:
                link_time = machine['LINK_STATUS']
                api_time = machine['API_STATUS']
                if api_time:
                    # 将api时间字符串转为datetime对象
                    api_time = datetime.strptime(api_time, '%Y/%m/%d %H:%M:%S')
                    # 判断当前时间与API时间的差距是否超过1分钟
                    if date_time - api_time < timedelta(seconds=75):
                        machine['API_STATUS'] = 'green'
                    else:
                        machine['API_STATUS'] = 'red'
                else:
                    machine['API_STATUS'] = 'gray'
                if link_time:
                    # 将link时间字符串转为datetime对象
                    link_time = datetime.strptime(link_time, '%Y/%m/%d %H:%M:%S')
                    # 判断当前时间与link时间的差距是否超过1分钟
                    if date_time - link_time < timedelta(seconds=75):
                        machine['LINK_STATUS'] = 'green'
                        machine['STARTUP_STATUS'] = 'OK'
                    else:
                        machine['LINK_STATUS'] = 'red'
                        get_data_from_server('update_machine_info',
                                             {'machine_pm': machine['MACHINE_PM'], 'STARTUP_STATUS': 'NG'},
                                             method='GET')
                        machine['STARTUP_STATUS'] = 'NG'

                else:
                    machine['LINK_STATUS'] = 'gray'

    # 返回查询结果和分页信息
    return render_template(
        'machine_info.html',
        machine_info=machine_info or [],
        query_params=query_params,
        server_url=server_url,
        total_count=total_count,
        total_pages=total_pages,
        current_page=page
    )


# 新增机台页面
@app.route('/machine_add', methods=['GET'])
def machine_add():
    server_url = current_app.config['SERVER_URL']
    emp_no = g.user.get('EMP_NO', '')
    return render_template('machine_add.html', server_url=server_url, emp_no=emp_no)


# 机台编辑页面
@app.route('/machine_edit', methods=['GET'])  # 编辑机器页面

def machine_edit():
    # 获取 URL 查询参数中的各个值
    machine_pm = request.args.get('machine_pm')
    machine_name = (request.args.get('machine_name') or '').strip()
    machine_ip = request.args.get('machine_ip')
    machine_port = request.args.get('machine_port')
    ipc_ip = request.args.get('ipc_ip')
    terminal_id = request.args.get('terminal_id')
    source_name = request.args.get('source_name')
    machine_type = request.args.get('machine_type')
    data_cleaning_flag = request.args.get('data_cleaning_flag')
    read_interval = request.args.get('read_interval')
    read_time_out = request.args.get('read_time_out')
    percentage = request.args.get('percentage')
    is_65_upload = request.args.get('is_65_upload')
    is_upload_working_rate = request.args.get('is_upload_working_rate')
    version = request.args.get('version')
    machine_building = request.args.get('machine_building')  # 0106 修復資料 新增欄位
    
    # 获取配置的服务器 URL
    server_url = current_app.config['SERVER_URL']
    update_machine_info_url = server_url + '/update_machine_info'

    # 渲染模板并传递获取到的参数
    return render_template('machine_edit.html',
                           machine_pm=machine_pm,
                           machine_name=machine_name,
                           machine_ip=machine_ip,
                           machine_port=machine_port,
                           ipc_ip=ipc_ip,
                           terminal_id=terminal_id,
                           source_name=source_name,
                           machine_type=machine_type,
                           data_cleaning_flag=data_cleaning_flag,
                           read_interval=read_interval,
                           read_time_out=read_time_out,
                           percentage=percentage,
                           is_65_upload=is_65_upload,
                           is_upload_working_rate=is_upload_working_rate,
                           version=version,
                           machine_building=machine_building,# 0106 修復資料 新增欄位
                           update_machine_info_url=update_machine_info_url)


# 参数信息页面
@app.route('/param_info', methods=['GET', 'POST'])
def param_info():
    server_url = current_app.config['SERVER_URL']
    # 假设从数据库或其他地方获取的数据
    query = "SELECT machine_pm as pm,machine_name as name FROM machine_info"
    pm_list = get_data_from_server('select', data={'query': query, 'params': []}, method='POST')
    if pm_list and 'error' not in pm_list:
        pm_list = pm_list['data']
    else:
        pm_list = []
    params = []
    # 获取查询参数
    machine_pm = request.args.get('machine_pm', '')
    machine_name = request.args.get('machine_name', '')

    query_params = {
        'machine_pm': machine_pm,
        'machine_name': machine_name
    }
    # 获取当前页码，默认为1
    page = int(request.args.get('page', 1))  # 从URL参数获取page，默认为第1页
    per_page = 15  # 每页显示15条记录
    total_count = 0  # 总记录数
    total_pages = 0  # 总页数

    if machine_pm:  # 如果有查询参数，则从服务器获取数据
        limit = " LIMIT %s OFFSET %s" % (per_page, (page - 1) * per_page)
        result = get_data_from_server('get_param_info', data={'machine_pm': machine_pm, 'limit': limit}, method='POST')
        if result and 'error' not in result:
            params = result['data']
            total_count = result['total_count']
            total_pages = (total_count // per_page) + (1 if total_count % per_page > 0 else 0)  # 计算总页数
    # 使用参数化查询传递参数
    return render_template('param_info.html', **query_params, pm_list=pm_list, query_params=query_params, params=params,
                           server_url=server_url, total_count=total_count, total_pages=total_pages, current_page=page)


# 添加参数页面
@app.route('/param_add', methods=['GET', 'POST'])
def param_add():
    server_url = current_app.config['SERVER_URL']
    machine_pm = request.args.get('machine_pm', '')  # 获取查询参数 machine_pm 的值，如果不存在则返回空字符串
    machine_name = request.args.get('machine_name', '')  # 获取查询参数 machine_name 的值，如果不存在则返回空字符串
    return render_template('param_add.html', server_url=server_url, machine_pm=machine_pm, machine_name=machine_name)


# 编辑参数页面
@app.route('/param_edit', methods=['GET'])
def param_edit():
    # 获取 URL 查询参数中的各个值
    machine_pm = request.args.get('machine_pm')
    machine_name = request.args.get('machine_name')
    param_name = request.args.get('param_name')
    param_address = request.args.get('param_address')
    param_unit = request.args.get('param_unit')
    read_bit = request.args.get('read_bit')
    is_read_hex = request.args.get('is_read_hex')
    param_multiply = request.args.get('param_multiply')
    param_id = request.args.get('param_id')

    # 获取配置的服务器 URL
    server_url = current_app.config['SERVER_URL']
    update_param_info_url = server_url + '/update_param_info'

    # 渲染模板并传递获取到的参数
    return render_template('param_edit.html',
                           machine_pm=machine_pm,
                           machine_name=machine_name,
                           param_name=param_name,
                           param_address=param_address,
                           param_unit=param_unit,
                           read_bit=read_bit,
                           is_read_hex=is_read_hex,
                           param_multiply=param_multiply,
                           param_id=param_id,
                           update_param_info_url=update_param_info_url)


# 相机信息页面
@app.route('/camera_info', methods=['GET', 'POST'])
def camera_info():
    server_url = current_app.config['SERVER_URL']
    # 假设从数据库或其他地方获取的数据
    query = "SELECT machine_pm as pm,machine_name as name FROM machine_info where machine_type like %s"
    pm_list = get_data_from_server('select', data={'query': query, 'params': ('%相机%',)}, method='POST')
    if pm_list and 'error' not in pm_list:
        pm_list = pm_list['data']
    else:
        pm_list = []
    cameras = []
    # 获取查询参数
    machine_pm = request.args.get('machine_pm', '')
    machine_name = request.args.get('machine_name', '')
    query_params = {
        'machine_pm': machine_pm,
        'machine_name': machine_name
    }
    if machine_pm:  # 如果有查询参数，则从服务器获取数据
        result = get_data_from_server('get_camera_config_api', data={'machine_pm': machine_pm}, method='POST')
        if result and 'error' not in result:
            for camera in result['data']:
                camera['MACHINE_NAME'] = machine_name
            cameras = result['data']
    else:
        result = get_data_from_server('select', data={
            'query': 'SELECT mi.MACHINE_NAME as MACHINE_NAME, ci.* FROM machine_info AS mi INNER JOIN camera_info AS ci ON mi.MACHINE_PM = ci.MACHINE_PM ORDER BY mi.MACHINE_NAME;'},
                                      method='POST')
        if result and 'error' not in result:
            cameras = result['data']
    if cameras:
        # 获取同步时间
        date_time = get_data_from_server('sync_time', method='GET')
        if date_time:
            date_time = datetime.strptime(date_time['server_time'], '%Y-%m-%d %H:%M:%S')
            for camera in cameras:
                link_time = camera['LINK_STATUS']
                if link_time:
                    # 将api时间字符串转为datetime对象
                    link_time = datetime.strptime(link_time, '%Y/%m/%d %H:%M:%S')
                    # 判断当前时间与API时间的差距是否超过一分钟
                    if date_time - link_time < timedelta(minutes=1):
                        camera['LINK_STATUS_COLOR'] = 'green'
                    else:
                        camera['LINK_STATUS_COLOR'] = 'red'
                else:
                    camera['LINK_STATUS_COLOR'] = 'gray'

    # 使用参数化查询传递参数
    return render_template('camera_info.html', pm_list=pm_list, query_params=query_params, cameras=cameras,
                           server_url=server_url)


# 添加相机页面
@app.route('/camera_add', methods=['GET', 'POST'])
def camera_add():
    server_url = current_app.config['SERVER_URL']
    machine_pm = request.args.get('machine_pm', '')  # 获取查询参数 machine_pm 的值，如果不存在则返回空字符串
    machine_name = request.args.get('machine_name', '')  # 获取查询参数 machine_name 的值，如果不存在则返回空字符串
    return render_template('camera_add.html', server_url=server_url, machine_pm=machine_pm, machine_name=machine_name)


# 编辑相机页面
@app.route('/camera_edit', methods=['GET'])
def camera_edit():
    # 获取 URL 查询参数中的各个值
    machine_pm = request.args.get('machine_pm')
    camera_ip = request.args.get('camera_ip')
    camera_port = request.args.get('camera_port')
    camera_type = request.args.get('camera_type')
    camera_position = request.args.get('camera_position')
    camera_agreement = request.args.get('camera_agreement')
    camera_id = request.args.get('camera_id')

    # 获取配置的服务器 URL
    server_url = current_app.config['SERVER_URL']
    update_camera_info_url = server_url + '/update_camera_info'

    # 渲染模板并传递获取到的参数
    return render_template('camera_edit.html',
                           machine_pm=machine_pm.strip(),
                           camera_ip=camera_ip,
                           camera_port=camera_port,
                           camera_type=camera_type,
                           camera_position=camera_position,
                           camera_agreement=camera_agreement,
                           camera_id=camera_id,
                           update_camera_info_url=update_camera_info_url)


# 工单信息页面
# @app.route('/work_order_info', methods=['GET', 'POST'])
# def work_order_info():
#     result = request.args
#     # 假设从数据库或其他地方获取的数据
#     query = "SELECT machine_pm as pm,machine_name as name FROM machine_info"
#     pm_list = get_data_from_server('select', data={'query': query}, method='POST')
#     if pm_list and 'error' not in pm_list:
#         pm_list = pm_list['data']
#     else:
#         pm_list = []
#     start_time = result.get('start_time', '')
#     end_time = result.get('end_time', '')
#     machine_pm = result.get('machine_pm', '')
#     machine_name = result.get('machine_name', '')
#     work_order = result.get('work_order', '')
#
#     error = ''
#     work_orders = []
#     page = int(request.args.get('page', 1))  # 从URL参数获取page，默认为第1页
#     per_page = 15  # 每页显示15条记录
#     total_count = 0  # 总记录数
#     total_pages = 0  # 总页数
#     if result:
#         # Step 1: 验证是否至少有 pm 或 工单
#         if not machine_pm and not work_order:
#             error = "必须提供 PM 或工单"
#         else:
#             # Step 2: 构造查询条件
#             query_conditions = []
#             query_params = []  # 用于存储实际的查询参数
#             # 添加 PM 条件
#             if machine_pm:
#                 query_conditions.append("work_order_info.machine_pm = %s")
#                 query_params.append(machine_pm)
#             # 添加 工单 条件
#             if work_order:
#                 query_conditions.append("work_order_info.work_order = %s")
#                 query_params.append(work_order)
#             # 时间条件
#             if start_time:
#                 query_conditions.append("work_order_info.start_time >= %s")
#                 query_params.append(start_time.replace('-', '/'))  # 使用短横线格式
#             if end_time:
#                 query_conditions.append("work_order_info.end_time <= %s")
#                 query_params.append(end_time.replace('-', '/'))  # 使用短横线格式
#             # Step 3: 合并查询条件
#             if query_conditions:
#                 count_query = "SELECT count(*) as total_count FROM work_order_info WHERE " + " AND ".join(
#                     query_conditions)
#                 result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm WHERE " + " AND ".join(
#                     query_conditions) + " ORDER BY work_order_info.start_time DESC"
#             else:
#                 count_query = "SELECT count(*) as total_count FROM work_order_info"
#                 result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm ORDER BY work_order_info.start_time DESC"
#             # Step 4: 执行查询
#             # 通过 `get_data_from_server` 方法传递查询语句和参数
#             total_count_info = get_data_from_server('select', data={'query': count_query, 'params': query_params},
#                                                     method='POST')
#             if total_count_info and total_count_info['data']:
#                 total_count = total_count_info['data'][0]['total_count']
#                 limit = " LIMIT %s OFFSET %s"  # 添加分页参数
#                 result_query += limit
#                 query_params.append(per_page)  # 每页显示的记录数
#                 query_params.append((page - 1) * per_page)  # 跳过的记录数
#                 work_orders = get_data_from_server('select', data={'query': result_query, 'params': query_params},
#                                                    method='POST')
#                 total_pages = (total_count // per_page) + (1 if total_count % per_page > 0 else 0)  # 计算总页数
#                 if not work_orders:
#                     work_orders = []
#                     error = "没有找到符合条件的工单信息"
#                 else:
#                     for _work_order in work_orders['data']:
#                         # 计算实际读取率
#                         _work_order['ACTUAL_READ_RATE'] = calculate_percentage(_work_order['IN_2DID'],
#                                                                                _work_order['OUT_2DID'])
#                         _work_order['READ_RATE'] = calculate_percentage(
#                             _work_order['IN_2DID'] if _work_order['IN_2DID'] > _work_order['OUT_2DID'] else _work_order[
#                                 'OUT_2DID'], _work_order['RTR_SUM_2DID'], is_change=False)
#                     work_orders = work_orders['data']
#
#     return render_template('work_order_info.html', pm_list=pm_list, start_time=start_time, end_time=end_time,
#                            machine_pm=machine_pm, machine_name=machine_name, work_order=work_order, error=error,
#                            work_orders=work_orders, total_count=total_count, total_pages=total_pages, current_page=page)
#
#


@app.route('/work_order_info', methods=['GET', 'POST'])
def work_order_info():
    # 假设从数据库或其他地方获取的数据
    query = "SELECT machine_pm as machine_pm,machine_name as machine_name FROM machine_info"
    result = get_data_from_server('select', data={'query': query}, method='POST')
    machine_info = []
    if result and 'error' not in result:
        machine_info = result['data']

    return render_template('work_order_info.html', machine_info=machine_info)

@app.route('/get_work_order_info', methods=['GET', 'POST'])
def get_work_order_info():
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        machine_pm = request.args.get('machine_pm_input')
        machine_name = request.args.get('machine_name_input')
        work_order = request.args.get('work_order_id')
        print(start_time, end_time, machine_pm, machine_name, work_order)
        # 时间字符串进行格式转换
        start_time = format_time(start_time)
        end_time = format_time(end_time)

        if start_time:
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d %H:%M:%S')
        if end_time:
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').strftime('%Y/%m/%d %H:%M:%S')

        # 构造查询条件
        query_conditions = []
        query_params = []  # 用于存储实际的查询参数

        # 添加 PM 条件
        if machine_pm:
            query_conditions.append("work_order_info.machine_pm = %s")
            query_params.append(machine_pm)

        # 添加 工单 条件
        if work_order:
            query_conditions.append("work_order_info.work_order = %s")
            query_params.append(work_order)

        # 时间条件
        if start_time:
            query_conditions.append("work_order_info.start_time >= %s")
            query_params.append(start_time)

        if end_time:
            query_conditions.append("work_order_info.start_time <= %s")
            query_params.append(end_time)

        # 合并查询条件
        if query_conditions:
            result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm WHERE " + " AND ".join(
                query_conditions) + " ORDER BY work_order_info.start_time DESC"
        else:
            result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm ORDER BY work_order_info.start_time DESC"

        # 执行查询
        # 通过 `get_data_from_server` 方法传递查询语句和参数
        work_order_info = get_data_from_server('select', data={'query': result_query, 'params': query_params},
                                                method='POST')

        if work_order_info and 'error' not in work_order_info:
            # 计算实际读取率
            for _work_order in work_order_info['data']:
                _work_order['ACTUAL_READ_RATE'] = calculate_percentage(_work_order['IN_2DID'],
                                                                       _work_order['OUT_2DID'])
                _work_order['READ_RATE'] = calculate_percentage(
                    _work_order['IN_2DID'] if _work_order['IN_2DID'] > _work_order['OUT_2DID'] else _work_order[
                        'OUT_2DID'], _work_order['RTR_SUM_2DID'], is_change=False)
            return jsonify({
                "work_order_info": work_order_info['data']
            })
        else:
            return jsonify({'error': "无相关工单信息"})
    except Exception as e:
        return jsonify({'error': str(e)})


# PDA信息页面
@app.route('/pda_info', methods=['GET', 'POST'])
def pda_info():
    server_url = current_app.config['SERVER_URL']
    pda_infos = get_data_from_server('get_all_pda_info', method='GET')
    return render_template('pda_info.html', pda_infos=pda_infos, server_url=server_url)


# 新增PDA页面
@app.route('/pda_add', methods=['GET'])
def pda_add():
    server_url = current_app.config['SERVER_URL']
    # 获取 URL 查询参数中的各个值
    pda_id = request.args.get('pda_id')
    pda_info = get_data_from_server('get_pda_info', data={'pda_id': pda_id}, method='GET')
    return render_template('pda_add.html', pda_info=pda_info, server_url=server_url)


# 编辑PDA页面
@app.route('/pda_edit', methods=['GET', 'POST'])
def pda_edit():
    # 获取 URL 查询参数中的各个值
    pda_id = request.args.get('pda_id')
    machine_pm = request.args.get('machine_pm')
    pda_ip = request.args.get('pda_ip')
    pda_use_emp = request.args.get('pda_use_emp')
    dcn_server_ip = request.args.get('dcn_server_ip')
    dcn_server_name = request.args.get('dcn_server_name')
    pda_sn = request.args.get('pda_sn')
    pda_mac = request.args.get('pda_mac')
    desc = request.args.get('desc')
    server_url = current_app.config['SERVER_URL']
    update_pda_info_url = server_url + '/update_pda_info'
    # 渲染模板并传递获取到的参数
    return render_template('pda_edit.html', pda_id=pda_id, machine_pm=machine_pm, pda_ip=pda_ip,
                           pda_use_emp=pda_use_emp, dcn_server_ip=dcn_server_ip, dcn_server_name=dcn_server_name,
                           pda_sn=pda_sn, pda_mac=pda_mac, desc=desc, update_pda_info_url=update_pda_info_url)


# 用户信息页面
@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    server_url = current_app.config['SERVER_URL']
    user_infos = get_data_from_server('get_user_info', method='GET')
    if user_infos and 'error' not in user_infos:
        pass
    else:
        user_infos = []
    return render_template('user_info.html', user_infos=user_infos, server_url=server_url)


# 新增用户页面
@app.route('/user_add', methods=['GET'])
def user_add():
    server_url = current_app.config['SERVER_URL']
    return render_template('user_add.html', server_url=server_url)


# 编辑用户页面
@app.route('/user_edit', methods=['GET', 'POST'])
def user_edit():
    # 获取 URL 查询参数中的各个值
    emp_no = request.args.get('emp_no')
    emp_name = request.args.get('emp_name')
    machine_pm = request.args.get('machine_pm')
    machine_name = request.args.get('machine_name')
    password = request.args.get('password')
    authority = request.args.get('authority')
    user_ip = request.args.get('user_ip')
    server_url = current_app.config['SERVER_URL']
    update_user_info_url = server_url + '/update_user_info'
    # 渲染模板并传递获取到的参数
    return render_template('user_edit.html', emp_no=emp_no, emp_name=emp_name, machine_pm=machine_pm,
                           machine_name=machine_name, password=password, authority=authority, user_ip=user_ip,
                           update_user_info_url=update_user_info_url)


# DCN 日志查询
@app.route('/dcn_log', methods=['GET', 'POST'])
def dcn_log():
    today_00_00_00 = datetime.now().strftime('%Y-%m-%d') + ' 00:00'
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {"start_time": today_00_00_00, "end_time": now, "dcn_ip": "", "work_order_id": "", "page": 1,
            "page_size": 50, "total_pages": 0}
    server_url = current_app.config['SERVER_URL']
    data['page'] = int(request.args.get('page', -1))
    if request.method == 'GET' and data['page'] != -1:
        data['start_time'] = request.args.get('start_time', today_00_00_00)
        data['end_time'] = request.args.get('end_time', now)
        data['dcn_ip'] = request.args.get('dcn_ip')
        data['work_order_id'] = request.args.get('work_order_id')
        if data['page'] == 0:
            data['page'] = 1
        # 格式化用户输入的 start_time 和 end_time
        data['start_time'] = format_time(data['start_time'])
        data['end_time'] = format_time(data['end_time'])

        where_query = []
        params = []
        if data['dcn_ip']:
            where_query.append("dcn_ip LIKE %s")
            params.append(f"%{data['dcn_ip']}%")
        if data['work_order_id']:
            where_query.append("message LIKE %s")
            params.append(f"%{data['work_order_id']}%")
        if data['start_time']:
            where_query.append("date_time >= %s")
            params.append(data['start_time'])
        if data['end_time']:
            where_query.append("date_time <= %s")
            params.append(data['end_time'])
        where_clause = " AND ".join(where_query) if where_query else "1=1"

        query = f"SELECT * FROM dcn_log_info WHERE {where_clause} ORDER BY date_time DESC LIMIT %s, %s;"
        total_pages_sql = f"SELECT COUNT(*) as total_pages FROM dcn_log_info WHERE {where_clause} ORDER BY date_time DESC;"

        result = get_data_from_server('select', data={'query': query,
                                                      'params': params + [(data['page'] - 1) * data['page_size'],
                                                                          data['page_size']]}, method="POST")
        total_pages_result = get_data_from_server('select', data={'query': total_pages_sql, 'params': params},
                                                  method="POST")
        error = ''
        if result and 'error' not in result:
            logs = result['data']
        else:
            if result and 'error' in result:
                error = result['error']
            else:
                error = '暂无数据'
            logs = []
        if total_pages_result and 'error' not in total_pages_result:
            data['total_pages'] = math.ceil(total_pages_result['data'][0]['total_pages'] / data['page_size'])

        return render_template('dcn_log.html', server_url=server_url, **data, logs=logs, error=error)

    return render_template('dcn_log.html', server_url=server_url, **data)


# IPC 日志查询
@app.route('/ipc_log', methods=['GET', 'POST'])
def ipc_log():
    return render_template('ipc_log.html')


@app.route('/ipc_log_info', methods=['GET', 'POST'])
def ipc_log_info():
    try:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        machine_pm = request.args.get('machine_pm')
        message = request.args.get('message')
        # 处理日期为短横线格式
        start_time = format_time(start_time)
        end_time = format_time(end_time)
        machien_info=get_data_from_server('get_machine_info_route',{"machine_pm": machine_pm},method='POST')
        if machien_info and 'error' not in machien_info:
            server_host =machien_info['IPC_IP']
        else:
            return jsonify({"error": "获取机台信息失败"}), 500
        data = {
            "server_host": server_host,
            "machine_pm": machine_pm,
            "message": "query",
            "start_time": start_time,
            "end_time": end_time,
        }
        if message:
            data['keyword']=message

        response = get_mes_data(data)
        if response and response.get('status','') == 'success':
            logs = [{"timestamp": row[2], "message": row[1]} for row in response.get('message',[])]
        elif response and response.get('error', ''):
            return jsonify({"error": response.get('error', '未获取到数据')}), 500
        else:
            return jsonify({"error": str('未获取到数据')}), 500
        return jsonify({
            "logs": logs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API测试网页
@app.route('/api_test', methods=['GET'])
def api_test():
    server_url = current_app.config['SERVER_URL']
    return render_template('api_test.html', server_url=server_url)


# WCF测试网页
@app.route('/wcf_test', methods=['GET'])
def wcf_test():
    server_url = current_app.config['SERVER_URL']
    return render_template('wcf_test.html', server_url=server_url)


# 获取机台参数
@app.route('/get_machine_params', methods=['GET'])
def get_machine_params():
    machine_pm = request.args.get('machine_pm')
    if machine_pm:
        # 获取机台参数
        machien_info=get_data_from_server('get_machine_info_route',{"machine_pm": machine_pm},method='POST')
        if machien_info and 'error' not in machien_info:
            server_host =machien_info['IPC_IP']
            machine_name = machien_info['MACHINE_NAME']
        else:
            return render_template('machine_params.html', error="获取机台信息失败", machine_pm=machine_pm)
        data = {
            "server_host": server_host,
            "machine_pm": machine_pm,
            "message": "read_param"
        }

        machine_params = get_mes_data(data)
        # 检查是否获取成功
        if machine_params and machine_params.get('status','') == 'success':
            parameters = machine_params.get('message', '')
            # 将参数字符串转换为字典列表
            data_list = []
            # 判断parameters是否列表
            if not isinstance(parameters, list):
                parameters = [parameters]
            for param in parameters:
                for item in param.split(','):
                    try:
                        # 正则匹配值和单位
                        match = re.match(r'([^:]+):\s*([^,\s]+)(?:\s+([^\s,]+))?', item.strip())
                        if match:
                            name, value, unit = match.groups() if len(match.groups()) == 3 else (*match.groups(), None)
                            data_dict = {
                                'name': name.strip(),
                                'value': value.strip(),
                                'unit': unit.strip() if unit else ''
                            }
                            data_list.append(data_dict)
                    except ValueError:
                        continue

            return render_template('machine_params.html', message=data_list, machine_pm=machine_pm,machine_name=machine_name)
        else:
            # 如果获取失败，返回失败信息
            message = '获取参数失败'
            return render_template('machine_params.html', error=message, machine_pm=machine_pm)
    # 如果没有提供 IPC IP 地址，返回错误信息
    return render_template('machine_params.html')


# 位置代号显示
@app.route('/location_code_info', methods=['GET'])
def location_code_info():
    server_url = current_app.config['SERVER_URL']
    locations = get_data_from_server(f'get_location_info', method='GET')
    # 修改键名的映射关系
    key_map = {'location_code': 'code', 'location_name': 'name', 'location_id': 'id'}
    # 遍历数据并修改键名
    for i, item in enumerate(locations):
        locations[i] = {key_map.get(k, k): v for k, v in item.items()}
    # 输出修改后的数据
    print(locations)
    return render_template('location_code_info.html', locations=locations, server_url=server_url)


# 工单数据导出
@app.route('/export_work_order_data/export', methods=['GET'])
def export_work_order_data():
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    machine_pm = request.args.get('machine_pm')
    machine_name = request.args.get('machine_name')
    work_order = request.args.get('work_order')
    query_conditions = []
    query_params = []  # 用于存储实际的查询参数
    # 添加 PM 条件
    if machine_pm:
        query_conditions.append("work_order_info.machine_pm = %s")
        query_params.append(machine_pm)
    # 添加 工单 条件
    if work_order:
        query_conditions.append("work_order_info.work_order = %s")
        query_params.append(work_order)
    # 时间条件
    if start_time:
        query_conditions.append("work_order_info.start_time >= %s")
        query_params.append(start_time.replace('-', '/'))  # 使用短横线格式
    if end_time:
        query_conditions.append("work_order_info.start_time <= %s")
        query_params.append(end_time.replace('-', '/'))  # 使用短横线格式
    # Step 3: 合并查询条件
    if query_conditions:
        result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm WHERE " + " AND ".join(
            query_conditions) + " ORDER BY work_order_info.start_time DESC"
    else:
        result_query = "SELECT work_order_info.*, machine_info.machine_name FROM work_order_info JOIN machine_info ON work_order_info.machine_pm = machine_info.machine_pm ORDER BY work_order_info.start_time DESC"
    # 通过 `get_data_from_server` 方法传递查询语句和参数
    total_count_info = get_data_from_server('select', data={'query': result_query, 'params': query_params},
                                            method='POST')
    # 定义英文键到中文键的映射
    key_mapping = {
        "COMPLETION_TIME": "完成时间",
        "EMP_NAME": "员工姓名",
        "END_TIME": "结束时间",
        "IN_2DID": "入口数量",
        "MACHINE_PM": "机台PM",
        "OUT_2DID": "出口数量",
        "PART_PN": "品目",
        "READ_RATE": "读取率",
        "RTR_SUM_2DID": "总工单数量",
        "START_TIME": "开始时间",
        "UPDATE_TIME": "更新时间",
        "WORK_ORDER": "工单号",
        "WORK_ORDER_2DID": "工单数量",
        "machine_name": "机台名称",
        "actual_read_rate": "实际读取率"
    }

    # 遍历列表中的每个字典，修改键名
    new_data = []
    for item in total_count_info['data']:
        item['actual_read_rate'] = calculate_percentage(item['IN_2DID'], item['OUT_2DID'])
        new_item = {key_mapping.get(key, key): value for key, value in item.items()}
        new_data.append(new_item)
    return new_data


# 快速生成器
@app.route('/barcode_qrcode_quick_generator', methods=['GET', 'POST'])
def barcode_qrcode_quick_generator():
    return render_template('BarcodeQRCodeQuickGenerator.html')


# 水电表信息
@app.route('/water_electricity_meter_info', methods=['GET', 'POST'])
def water_electricity_meter_info():
    server_url = current_app.config['SERVER_URL']
    if request.method == 'POST':
        machine_pm = request.form.get('machine_pm')
        electricity_meter_info = get_data_from_server('meter_info\{}'.format(machine_pm), method='GET')
    else:
        electricity_meter_info = get_data_from_server('meter_info', method='GET')
    if not electricity_meter_info:
        electricity_meter_info = []
    return render_template('water_electricity_meter_info.html', electricity_meter_info=electricity_meter_info,
                           server_url=server_url)


# 编辑水电表信息
@app.route('/edit_water_electricity_meter_info', methods=['GET', 'POST'])
def edit_water_electricity_meter_info():
    result = request.args
    id = result.get('id')
    machine_pm = result.get('machine_pm')
    meter_code = result.get('meter_code')
    meter_type = result.get('meter_type')
    description = result.get('description')
    server_url = current_app.config['SERVER_URL']
    update_water_electricity_meter_info = server_url + '/update_water_electricity_meter_info'
    return render_template('edit_water_electricity_meter_info.html', id=id, machine_pm=machine_pm,
                           meter_code=meter_code, meter_type=meter_type, description=description, server_url=server_url,
                           update_water_electricity_meter_info=update_water_electricity_meter_info)


# 新增水电表信息
@app.route('/add_water_electricity_meter_info', methods=['GET', 'POST'])
def add_water_electricity_meter_info():
    server_url = current_app.config['SERVER_URL']
    return render_template('add_water_electricity_meter_info.html', server_url=server_url)


@app.route('/production_records', methods=['GET', 'POST'])
def production_records():
    server_url = current_app.config['SERVER_URL']
    return render_template('production_records.html', server_url=server_url)


# ---------------------------------------------------------------------------

def get_mes_data(data):
    try:
        if not data:
           return {"error": "请求中缺少有效的 JSON 数据"}

        # 获取服务器地址
        server_host = data.get('server_host')
        server_port = 6789
        if not server_host:
            return {"error": "请求中缺少有效的服务器地址信息"}
        # 提取要发送给服务器的数据
        send_data = {
            key: value for key, value in data.items()
            if key != 'server_host'
        }
        # 创建一个 TCP 套接字
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 连接到服务器
            s.connect((server_host, server_port))
            # 将数据转换为 JSON 字符串并编码
            json_data = json.dumps(send_data).encode('utf-8')

            # 发送数据到服务器
            s.sendall(json_data)
            # 循环接收数据
            buffer = b""
            while True:
                recv_data = s.recv(1024)
                if not recv_data:
                    break
                buffer += recv_data
            try:
                # 解析接收到的完整数据
                response_data = json.loads(buffer.decode('utf-8'))
                return response_data
            except json.JSONDecodeError:
                return {"error": "接收到的数据不是有效的 JSON 格式。"}
    except Exception as e:
        return {"error": f"连接服务器时出现错误: {str(e)}"}


def send_tcp_command(server_ip, server_port, command):
    try:
        # 创建一个 TCP 套接字
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 连接到服务器
            s.connect((server_ip, server_port))
            # 发送指令
            s.sendall(command.encode('utf-8'))
            print(f"已发送指令: {command}")
            # 接收服务器的响应
            response = s.recv(1024).decode('utf-8')
            print(f"服务器响应: {response}")
            return response
    except Exception as e:
        print(f"发送指令时出错: {e}")
        return None


@app.route('/send_tcp_command', methods=['GET','POST'])
def api_send_tcp_command():
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求中缺少有效的 JSON 数据"}), 400
    server_ip = data.get('server_ip')
    server_port = 12345
    command = data.get('command')
    if not server_ip or not server_port or not command:
        return jsonify({"error": "请求中缺少必要的参数（server_ip、server_port 或 command）"}), 400
    result = send_tcp_command(server_ip, server_port, command)
    if result is not None:
        # 去除结果中的首尾空白字符
        result = result.strip()
        return jsonify({"status": "success", "message": result}), 200
    else:
        return jsonify({"status": "error", "error": "发送指令时出现错误，请检查服务器连接和参数"}), 500

"""==========================================51K=================================================="""
# 51K 机台信息
@app.route('/51k_machine_info', methods=['GET', 'POST'])
def get_51k_machine_info():
    return render_template('51kmachine_info.html')

@app.route('/51k_machine_data', methods=['GET', 'POST'])
def _51k_machine_data():
    data = {
        'query': "SELECT * FROM machine_info WHERE DEPARTMENT='51K'"
    }
    result = get_data_from_server('select',data=data, method='POST')
    if result and 'error' not in result:
        machine_data = result['data']
    else:
        machine_data = []
    return jsonify({'machine_data': machine_data}),200

# 新增51K机台信息
@app.route('/add_51k_machine_info', methods=['GET', 'POST'])
def add_51k_machine_info():
    try:
        # 获取前端发送的 JSON 数据
        data = request.get_json()
        # 提取机台信息
        pm = data.get('MACHINE_PM')
        name = data.get('MACHINE_NAME')
        ipc_ip = data.get('IPC_IP')
        terminal_id = data.get('TERMINAL_ID')
        source_name = data.get('SOURCE_NAME')


        # 检查必要的字段是否存在
        if not name:
            return jsonify({"success": False, "message": "机台名称不能为空"}), 400
        # 创建新的机台项
        new_item = {
            "machine_pm": pm,
            "machine_name": name,
            "ipc_ip": ipc_ip,
            "terminal_id": terminal_id,
            "source_name": source_name,
            "department": "51K",
            "machine_type": "LOG",
            "is_65_upload": "True",
            "is_upload_working_rate": "False",
            "data_cleaning_flag": "False",
            "read_interval":10,
            "read_time_out":120,
            "emp_no": "U2308583",
            "machine_ip":ipc_ip
        }
        # 发送请求到服务器
        result = get_data_from_server('add_machine_info', data=new_item, method='POST')
        if result and 'message' in result:
            update_info=get_data_from_server('update_machine_info', data={"machine_pm": pm,"department": "51K"}, method='POST')
            return jsonify({"success": True, "newItem": new_item})
        else:
            return jsonify({"success": False, "message": "新增机台信息失败"}), 500
    except Exception as e:
        # 处理异常并返回错误响应
        return jsonify({"success": False, "message": str(e)}), 500

# 删除51K机台信息
@app.route('/delete_51k_machine_info', methods=['GET', 'POST'])
def delete_51k_machine_info():
    try:
        # 获取前端发送的 JSON 数据
        data = request.get_json()
        # 提取机台信息
        pm = data.get('MACHINE_PM')
        # 检查必要的字段是否存在
        if not pm:
            return jsonify({"success": False, "message": "机台 PM 不能为空"}), 400
        # 发送请求到服务器
        result = get_data_from_server('del_machine_info', data=[pm], method='POST')
        print(result)
        if result and 'error' not in result:
            return jsonify({"success": True, "message": "删除机台信息成功"})
        else:
            return jsonify({"success": False, "message": "删除机台信息失败"}), 500
    except Exception as e:
        # 处理异常并返回错误响应
        return jsonify({"success": False, "message": str(e)}), 500

# 编辑51K机台信息
@app.route('/edit_51k_machine_info/<string:machine_name>', methods=['PUT'])
def edit_51k_machine_info(machine_name):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求体中缺少 JSON 数据"}), 400
        # 提取机台信息
        pm = data.get('MACHINE_PM')
        name = data.get('MACHINE_NAME')
        ipc_ip = data.get('IPC_IP')
        terminal_id = data.get('TERMINAL_ID')
        source_name = data.get('SOURCE_NAME')
        # 检查必要的字段是否存在
        if not name:
            return jsonify({"success": False, "message": "机台名称不能为空"}), 400
        data = {
            "machine_pm": pm,
            "machine_name": name,
            "ipc_ip": ipc_ip,
            "terminal_id": terminal_id,
            "source_name": source_name,
            "department": "51K",
            "machine_type": "LOG",
            "is_65_upload": "True",
            "is_upload_working_rate": "False",
            "data_cleaning_flag": "False",
            "read_interval":10,
            "read_time_out":120,
            "emp_no": "U2308583",
            "machine_ip":ipc_ip
        }
        # 发送请求到服务器
        update_info = get_data_from_server('update_machine_info', data=data,
                                           method='POST')
        if update_info and 'error' not in update_info:
            return jsonify({"success": True, "message": "机台信息编辑成功"}), 200
        else:
            return jsonify({"success": False, "message": "未找到指定名称的机台信息"}), 404

    except Exception as e:
        return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500

# 指定要显示的文件夹路径
UPLOAD_FOLDER = r'C:\Users\Administrator\Desktop\资料'


def get_file_structure(path):
    structure = []
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            sub_structure = get_file_structure(item_path)
            structure.append({
                'name': item,
                'is_folder': True,
                'children': sub_structure
            })
        else:
            structure.append({
                'name': item,
                'is_folder': False
            })
    return structure


@app.route('/file_download', defaults={'path': ''})
@app.route('/file_download/<path:path>')
def file_download(path):
    full_path = os.path.join(UPLOAD_FOLDER, path)
    file_structure = get_file_structure(full_path)
    current_path = path
    return render_template('file_download.html', file_structure=file_structure, current_path=current_path)


@app.route('/download', methods=['POST'])
def download():
    selected_files = request.form.getlist('selected_files')
    if not selected_files:
        return "未选择任何文件"
    for file in selected_files:
        file_path = os.path.join(UPLOAD_FOLDER, file)
        if os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True)
    return "所选文件均不存在"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7414, debug=True, use_reloader=False)
