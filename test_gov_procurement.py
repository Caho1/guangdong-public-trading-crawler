#!/usr/bin/env python3
"""测试政府采购-中标结果公告接口"""
import requests
import json

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
})

# 1. 测试列表接口
print("=" * 60)
print("测试列表接口")
print("=" * 60)

resp = session.post(f"{BASE}/search/v2/items", json={
    "type": "trading-type",
    "openConvert": False,
    "keyword": "",
    "siteCode": "44",
    "secondType": "D",  # 政府采购
    "tradingProcess": "553,3871,2871,2873",  # 中标结果公告
    "thirdType": "[]",
    "projectType": "",
    "publishStartTime": "",
    "publishEndTime": "",
    "pageNo": 1,
    "pageSize": 3
})

data = resp.json()
print(f"总记录数: {data['data']['total']}")
print(f"总页数: {data['data']['pageTotal']}")
print(f"\n前3条记录:\n")

for i, item in enumerate(data['data']['pageData'], 1):
    print(f"[{i}] {item['noticeTitle']}")
    print(f"    项目编号: {item['projectCode']}")
    print(f"    发布时间: {item['publishDate']}")
    print(f"    noticeId: {item['noticeId']}")
    print(f"    tradingProcess: {item['tradingProcess']}")
    print(f"    regionCode: {item.get('regionCode', 'N/A')}")
    print(f"    siteCode: {item['siteCode']}")
    print(f"    edition: {item['edition']}")
    print()

# 2. 测试第一条记录的详情接口
print("=" * 60)
print("测试详情接口（不使用 nodeId）")
print("=" * 60)

item = data['data']['pageData'][0]

# 尝试不传 nodeId
params = {
    "noticeId": item['noticeId'],
    "projectCode": item['projectCode'],
    "bizCode": item['tradingProcess'],
    "siteCode": item.get('regionCode', item['siteCode']),
    "version": item['edition'],
    "tradingType": item['noticeSecondType'],
}

print(f"请求参数: {json.dumps(params, ensure_ascii=False, indent=2)}\n")

resp = session.get(f"{BASE}/center/apis/trading-notice/new/detail", params=params)
print(f"状态码: {resp.status_code}")

if resp.status_code == 200:
    detail = resp.json()
    if detail.get('errcode') == 0:
        print("✅ 成功获取详情（无需 nodeId）\n")
        print(f"标题: {detail['data']['title']}")
        print(f"发布时间: {detail['data']['publishDate']}")

        # 提取结构化信息
        for col in detail['data'].get('tradingNoticeColumnModelList', []):
            if col.get('multiKeyValueTableList'):
                print(f"\n【{col['name']}】")
                for table in col['multiKeyValueTableList']:
                    for kv in table[:5]:  # 只显示前5个
                        print(f"  {kv['key']}: {kv.get('value', '')}")
    else:
        print(f"❌ 接口返回错误: {detail.get('errmsg')}")
else:
    print(f"❌ 请求失败: {resp.text[:200]}")

# 3. 测试是否需要 nodeList 接口
print("\n" + "=" * 60)
print("测试 nodeList 接口")
print("=" * 60)

resp = session.get(f"{BASE}/center/apis/trading-notice/new/nodeList", params={
    "siteCode": item.get('regionCode', item['siteCode']),
    "tradingType": item['noticeSecondType'],
    "bizCode": item['tradingProcess'],
    "projectCode": item['projectCode'],
    "classify": item.get('projectType', ''),
})

if resp.status_code == 200:
    nodes = resp.json()
    if nodes.get('errcode') == 0:
        print("✅ nodeList 接口可用\n")
        for node in nodes['data']:
            print(f"  {node['nodeName']}: nodeId={node['nodeId']}, dataCount={node.get('dataCount', 0)}")
    else:
        print(f"⚠️  nodeList 接口返回: {nodes.get('errmsg')}")
else:
    print(f"⚠️  nodeList 接口不可用")
