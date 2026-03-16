import requests
import time
from bs4 import BeautifulSoup
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
        except Exception as e:
            if i == 2:
                raise
            time.sleep(2)

def get_items(page_no=1):
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

def extract_prices_from_html(html_content):
    """从HTML中提取价格信息"""
    soup = BeautifulSoup(html_content, 'lxml')
    results = []

    # 查找所有表格
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue

        # 获取表头
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]

        # 查找包含价格相关的列
        price_keywords = ['报价', '价格', '金额', '投标报价', '中标金额']
        has_price = any(any(kw in h for kw in price_keywords) for h in headers)

        if has_price:
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if cells:
                    results.append(dict(zip(headers, cells)))

    return results

if __name__ == "__main__":
    print("开始提取招标价格信息...\n")

    data = get_items(page_no=1)

    for i, item in enumerate(data["pageData"][:3], 1):
        print(f"{'='*80}")
        print(f"[{i}] {item['noticeTitle'][:60]}...")

        node_id = get_node_id(item)
        if not node_id:
            print("未找到nodeId\n")
            continue

        detail = get_detail(item, node_id)

        # 提取HTML内容
        for col in detail.get("tradingNoticeColumnModelList", []):
            if col.get("viewStyle") == "richText":
                html = col.get("richtext", "")
                prices = extract_prices_from_html(html)

                if prices:
                    print(f"\n提取到 {len(prices)} 条价格信息：")
                    for j, price_info in enumerate(prices, 1):
                        print(f"\n  [{j}]")
                        for key, value in price_info.items():
                            if value:
                                print(f"    {key}: {value}")
                else:
                    print("\n未找到价格信息")
                break

        print()
        time.sleep(0.8)

    print("提取完成!")
