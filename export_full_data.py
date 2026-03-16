import requests
import time
import csv
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

def extract_detail_info(detail):
    """提取详情页面的结构化数据"""
    info = {}
    for col in detail.get("tradingNoticeColumnModelList", []):
        if col.get("viewStyle") == "keyTable" and col.get("multiKeyValueTableList"):
            for table in col["multiKeyValueTableList"]:
                for kv in table:
                    info[kv["key"]] = kv["value"]
    return info

def extract_prices_from_html(html_content):
    soup = BeautifulSoup(html_content, 'lxml')
    results = []
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
        price_keywords = ['报价', '价格', '金额', '投标报价', '中标金额']
        if any(any(kw in h for kw in price_keywords) for h in headers):
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if cells:
                    results.append(dict(zip(headers, cells)))
    return results

if __name__ == "__main__":
    print("开始导出完整数据到CSV...\n")

    # 第一遍：收集所有字段
    print("第1步：扫描数据，收集所有字段...")
    all_fields = set()

    for page in range(1, 3):
        data = get_items(page_no=page)
        for item in data["pageData"]:
            try:
                node_id = get_node_id(item)
                if node_id:
                    detail = get_detail(item, node_id)
                    info = extract_detail_info(detail)
                    all_fields.update(info.keys())
                time.sleep(0.8)
            except:
                pass

    # 构建CSV列
    base_cols = ['公告标题', '项目代码', '发布时间']
    detail_cols = sorted(list(all_fields))
    price_cols = ['投标单位', '报价（元）']
    headers = base_cols + detail_cols + price_cols

    print(f"找到 {len(detail_cols)} 个详情字段")
    print(f"CSV列数: {len(headers)}\n")

    # 第二遍：写入数据
    print("第2步：写入CSV文件...")
    csv_file = "/Users/bystanders/Desktop/公共资源交易/招标完整数据.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for page in range(1, 3):
            print(f"  处理第 {page} 页...")
            data = get_items(page_no=page)

            for item in data["pageData"]:
                try:
                    node_id = get_node_id(item)
                    if not node_id:
                        continue

                    detail = get_detail(item, node_id)
                    detail_info = extract_detail_info(detail)

                    # 提取价格
                    prices = []
                    for col in detail.get("tradingNoticeColumnModelList", []):
                        if col.get("viewStyle") == "richText":
                            prices = extract_prices_from_html(col.get("richtext", ""))
                            break

                    # 写入数据
                    if prices:
                        for price_info in prices:
                            row = [item['noticeTitle'], item['projectCode'], item['publishDate']]
                            row += [detail_info.get(field, '') for field in detail_cols]
                            row += [
                                price_info.get('单位名称', ''),
                                price_info.get('报价（元）', price_info.get('报价', ''))
                            ]
                            writer.writerow(row)
                    else:
                        row = [item['noticeTitle'], item['projectCode'], item['publishDate']]
                        row += [detail_info.get(field, '') for field in detail_cols]
                        row += ['', '']
                        writer.writerow(row)

                    time.sleep(0.8)
                except Exception as e:
                    print(f"    错误: {str(e)[:50]}")

    print(f"\n导出完成! 文件: {csv_file}")
