# -*- coding: utf-8 -*-
"""探针：字典数据同类型同 dictValue 是否可重复落库+消费端影响（调试手段，不留痕）。"""
import sys, traceback
sys.path.insert(0, '/home/irons/dev/ruoyi-regression')
sys.path.insert(0, '/home/irons/dev/ruoyi-regression/exec')
from api import admin_token, get, post, delete, db, redis_get, uniq
from contract_lib import ensure_dict_type, delete_dict_type

def main():
    tok = admin_token()
    did, dt = ensure_dict_type('pdu')
    try:
        body1 = dict(dictLabel='标签A', dictValue='dupval', dictType=dt, status='0',
                     dictSort=1, cssClass='', listClass='', isDefault='N')
        body2 = dict(body1, dictLabel='标签B', dictSort=2)
        h1, r1 = post('/system/dict/data', body1, token=tok)
        h2, r2 = post('/system/dict/data', body2, token=tok)
        print('add1:', h1, r1.get('code'), r1.get('msg'))
        print('add2:', h2, r2.get('code'), r2.get('msg'))
        rows = db("select dict_code,dict_label,dict_value from sys_dict_data "
                  "where dict_type=%s and dict_value='dupval' order by dict_code", (dt,))
        print('DB rows:', rows)
        h3, r3 = get('/system/dict/data/type/' + dt, token=tok)
        print('consume /type:', [(x.get('dictLabel'), x.get('dictValue')) for x in (r3.get('data') or [])])
        cache = redis_get('sys_dict:' + dt)
        print('cache head:', (cache or '')[:260])
        h4, r4 = get('/system/dict/data/list', token=tok,
                     params=dict(dictType=dt, dictValue='dupval', pageNum=1, pageSize=10))
        print('list by value total:', r4.get('total'),
              [x.get('dictLabel') for x in (r4.get('rows') or [])])
        for x in rows:
            delete('/system/dict/data/' + str(x['dict_code']), token=tok)
    finally:
        delete_dict_type(did)
        print('cleanup residue:', db("select count(*) as c from sys_dict_data where dict_type=%s", (dt,)))

if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
