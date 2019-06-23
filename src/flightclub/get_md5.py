#!/usr/bin/env python3

import hashlib

login_form = {
    # fixed
    'accessToken': '',
    'code': '',
    'expire': '0',
    'mode': '0',
    'openId': '',
    'sourcePage': '',
    'platform': 'iPhone',
    'refreshToken': '',
    'token': 'JLIjsdLjfsdII%3D%7CMTQxODg3MDczNA%3D%3D%7C07aaal32795abdeff41cc9633329932195',
    'shumeiid': '201906191136236fded65cbbdfa090f71e09578a0feac101227030b29a0ef5',
    'v': '4.2.1',

    # per user fixed
    'countryCode': '1',
    'userName': '4243338516',
    'password': 'c00d0cf35e1bf706933662476b7c8e4c',
    'uuid': '1C6BD899-8A6A-4E9A-BCA8-9E6BA149D7A7',
    'type': 'pwd',
    
    # may need to change
    'timestamp': '1561177360584',
    'sign': 'ee2e8b977be6a8f8220ddd2d002ad9cb'
}


def get_md5(str):
    m1 = hashlib.md5()
    # 使用md5对象里的update方法md5转换
    m1.update(str.encode("GBK"))
    sign = m1.hexdigest()
    return sign

def get_sign(api_params):
    hash_map = {}
    for k in api_params:
        hash_map[k] = api_params[k]

    hash_map = sorted(hash_map.items(), key=lambda x: x[0])

    str = ''
    for v in hash_map:
        str += v[0] + v[1]

    # 生成一个md5对象
    m1 = hashlib.md5()
    # 使用md5对象里的update方法md5转换
    m1.update(str.encode("GBK"))
    sign = m1.hexdigest()
    return sign

sign = get_sign(login_form)
print('got:  ', sign)

print('want: ', 'ee2e8b977be6a8f8220ddd2d002ad9cb')
print(get_md5('https://m.poizon.com/users/unionLogin?accessToken=&code=&expire=0&mode=0&openId=&sourcePage=&platform=iPhone&refreshToken=&token=JLIjsdLjfsdII%253D%257CMTQxODg3MDczNA%253D%253D%257C07aaal32795abdeff41cc9633329932195&shumeiid=201906191136236fded65cbbdfa090f71e09578a0feac101227030b29a0ef5&v=4.2.1&countryCode=1&userName=4243338516&password=c00d0cf35e1bf706933662476b7c8e4c&uuid=1C6BD899-8A6A-4E9A-BCA8-9E6BA149D7A7&type=pwd&timestamp=1561177360584'))
