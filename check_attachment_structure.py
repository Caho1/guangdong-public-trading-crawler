import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.trust_env = False
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

def safe_request(func, *args, **kwargs):
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except:
            if i == 2:
                raise

# 直接获取第一个有附件的项目完整数据
data = safe_request(session.post, f"{BASE}/search/v2/items", json={
    "type": "trading-type",
    "openConvert": False,
    "keyword": "",
    "siteCode": "44",
    "secondType": "A",
    "tradingProcess": "",
    "thirdType": "[]",
    "projectType": "",
    "pageNo": 1,
    "pageSize": 10
}).json()["data"]

item = data["pageData"][0]

# 获取nodeId
resp = safe_request(session.get, f"{BASE}/center/apis/trading-notice/new/nodeList", params={
    "siteCode": item["regionCode"],
    "tradingType": item["noticeSecondType"],
    "bizCode": item["tradingProcess"],
    "projectCode": item["projectCode"],
    "classify": item["projectType"]
})

node_id = None
for node in resp.json()["data"]:
    if node["selectedBizCode"] == item["tradingProcess"]:
        node_id = node["nodeId"]
        break

# 获取详情
detail_resp = safe_request(session.get, f"{BASE}/center/apis/trading-notice/new/detail", params={
    "nodeId": node_id,
    "version": item["edition"],
    "tradingType": item["noticeSecondType"],
    "noticeId": item["noticeId"],
    "bizCode": item["tradingProcess"],
    "projectCode": item["projectCode"],
    "siteCode": item["regionCode"]
})

detail = detail_resp.json()["data"]

print("完整详情数据结构：")
print(json.dumps(detail, indent=2, ensure_ascii=False))
