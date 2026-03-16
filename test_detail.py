import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.trust_env = False
retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

def safe_request(func, *args, **kwargs):
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)

# 测试数据
test_cases = [
    {
        "title": "广州从化区禾仓村城中村改造项目姓龙围地块复建安置房建设项目二期设计施工总承包招标公告",
        "projectCode": "E4401002701501906001",
        "nodeId": "2005939215280603137"
    },
    {
        "title": "广州从化区东风村城中村改造项目02地块复建安置房建设项目二期设计施工总承包招标公告",
        "projectCode": "E4401002701501896001",
        "nodeId": "2005939215280603137"
    },
    {
        "title": "四会市县城排水排涝工程--贞山街道排涝能力提升工程第二期（施工）中标候选人公示",
        "projectCode": "E4412010813001313001",
        "nodeId": "2015595785584369686"
    }
]

def get_items_by_project_code(project_code):
    """通过项目代码搜索获取完整信息"""
    resp = safe_request(session.post, f"{BASE}/search/v2/items", json={
        "type": "trading-type",
        "openConvert": False,
        "keyword": project_code,
        "siteCode": "44",
        "secondType": "",
        "tradingProcess": "",
        "thirdType": "[]",
        "projectType": "",
        "publishStartTime": "",
        "publishEndTime": "",
        "pageNo": 1,
        "pageSize": 10
    })
    data = resp.json()["data"]
    if data["pageData"]:
        return data["pageData"][0]
    return None

def get_detail(item, node_id):
    """获取详情"""
    resp = safe_request(session.get, f"{BASE}/center/apis/trading-notice/new/detail", params={
        "nodeId": node_id,
        "version": item["edition"],
        "tradingType": item["noticeSecondType"],
        "noticeId": item["noticeId"],
        "bizCode": item["tradingProcess"],
        "projectCode": item["projectCode"],
        "siteCode": item["regionCode"]
    })
    return resp.json()["data"]

if __name__ == "__main__":
    print("开始测试3个项目的详细信息...\n")

    # 先获取第2页数据
    resp = safe_request(session.post, f"{BASE}/search/v2/items", json={
        "type": "trading-type",
        "openConvert": False,
        "keyword": "",
        "siteCode": "44",
        "secondType": "A",
        "tradingProcess": "",
        "thirdType": "[]",
        "projectType": "",
        "publishStartTime": "",
        "publishEndTime": "",
        "pageNo": 2,
        "pageSize": 10
    })
    items = resp.json()["data"]["pageData"][:3]

    for i, item in enumerate(items, 1):
        print(f"{'='*80}")
        print(f"[{i}] {item['noticeTitle'][:50]}...")
        print(f"项目代码: {item['projectCode']}")

        # 获取nodeId
        resp2 = safe_request(session.get, f"{BASE}/center/apis/trading-notice/new/nodeList", params={
            "siteCode": item["regionCode"],
            "tradingType": item["noticeSecondType"],
            "bizCode": item["tradingProcess"],
            "projectCode": item["projectCode"],
            "classify": item["projectType"]
        })
        node_id = None
        for node in resp2.json()["data"]:
            if node["selectedBizCode"] == item["tradingProcess"]:
                node_id = node["nodeId"]
                break

        if not node_id:
            print("❌ 未找到nodeId\n")
            continue

        print(f"NodeId: {node_id}")
        detail = get_detail(item, node_id)
        print(f"\n标题: {detail['title']}")
        print(f"发布时间: {detail['publishDate']}")

        for col in detail.get("tradingNoticeColumnModelList", []):
            print(f"\n--- {col['name']} ---")

            if col.get("viewStyle") == "richText":
                content = col.get("richtext", "")
                print(f"正文长度: {len(content)} 字符")
                print(f"正文预览: {content[:200]}...")

            elif col.get("viewStyle") == "keyTable":
                if col.get("multiKeyValueTableList"):
                    for table in col["multiKeyValueTableList"]:
                        for kv in table[:5]:
                            print(f"  {kv['key']}: {kv['value']}")
                        if len(table) > 5:
                            print(f"  ... 还有 {len(table)-5} 项")

            elif col.get("noticeFileBOList"):
                print(f"附件数量: {len(col['noticeFileBOList'])}")
                for f in col["noticeFileBOList"][:3]:
                    print(f"  - {f.get('fileName', 'N/A')}")

        print()
        time.sleep(1)

    print("测试完成!")
