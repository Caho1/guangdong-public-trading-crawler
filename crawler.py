import requests
import time
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
    """带重试的请求包装"""
    for i in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)

def get_items(page_no=1):
    """获取列表数据"""
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
        "pageNo": page_no,
        "pageSize": 10
    })
    return resp.json()["data"]

def get_node_id(item):
    """获取 nodeId"""
    resp = safe_request(session.get, f"{BASE}/center/apis/trading-notice/new/nodeList", params={
        "siteCode": item["regionCode"],
        "tradingType": item["noticeSecondType"],
        "bizCode": item["tradingProcess"],
        "projectCode": item["projectCode"],
        "classify": item["projectType"]
    })
    for node in resp.json()["data"]:
        if node["selectedBizCode"] == item["tradingProcess"]:
            return node["nodeId"]
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
    print("开始测试爬取5页数据...")
    total_count = 0

    for page in range(1, 6):
        print(f"\n{'='*60}")
        print(f"第 {page} 页")
        print('='*60)

        try:
            data = get_items(page_no=page)
            print(f"总数: {data['total']}, 当前页: {data['pageNo']}/{data['pageTotal']}")

            for i, item in enumerate(data["pageData"], 1):
                total_count += 1
                print(f"\n[{total_count}] {item['noticeTitle']}")
                print(f"    项目代码: {item['projectCode']}")

                try:
                    node_id = get_node_id(item)
                    if node_id:
                        print(f"    NodeId: {node_id}")
                        detail = get_detail(item, node_id)
                        print(f"    发布时间: {detail['publishDate']}")

                        for col in detail.get("tradingNoticeColumnModelList", []):
                            if col.get("viewStyle") == "richText":
                                content = col.get("richtext", "")
                                print(f"    正文长度: {len(content)} 字符")
                                break
                    else:
                        print("    未找到匹配的 nodeId")
                except Exception as e:
                    print(f"    错误: {e}")

                time.sleep(0.8)

            time.sleep(1)

        except Exception as e:
            print(f"第 {page} 页失败: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"测试完成! 共爬取 {total_count} 条数据")
    print('='*60)
