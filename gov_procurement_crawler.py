#!/usr/bin/env python3
"""政府采购-中标结果公告爬虫"""
import csv
import json
import os
import time
import requests
from bs4 import BeautifulSoup
import html2text

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"
OUTPUT_DIR = "政府采购数据"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
})

# 创建输出目录
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/json", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/markdown", exist_ok=True)

def get_items(page_no=1, page_size=10):
    """获取中标结果公告列表"""
    resp = session.post(f"{BASE}/search/v2/items", json={
        "type": "trading-type",
        "openConvert": False,
        "keyword": "",
        "siteCode": "44",
        "secondType": "D",
        "tradingProcess": "553,3871,2871,2873",
        "thirdType": "[]",
        "projectType": "",
        "publishStartTime": "",
        "publishEndTime": "",
        "pageNo": page_no,
        "pageSize": page_size,
    })
    resp.raise_for_status()
    data = resp.json()
    assert data["errcode"] == 0
    return data["data"]

def get_node_list(item):
    """获取项目节点列表"""
    resp = session.get(f"{BASE}/center/apis/trading-notice/new/nodeList", params={
        "siteCode": item.get('regionCode', item['siteCode']),
        "tradingType": item['noticeSecondType'],
        "bizCode": item['tradingProcess'],
        "projectCode": item['projectCode'],
        "classify": item.get('projectType', ''),
    })
    resp.raise_for_status()
    data = resp.json()
    if data["errcode"] != 0:
        return []
    return data["data"]

def find_node_id(item, node_list):
    """从节点列表中匹配 nodeId"""
    for node in node_list:
        if node.get("selectedBizCode") == item["tradingProcess"]:
            return node["nodeId"]
    for node in node_list:
        if node.get("dataCount", 0) > 0:
            return node["nodeId"]
    return None

def get_detail(item, node_id):
    """获取公告详情"""
    resp = session.get(f"{BASE}/center/apis/trading-notice/new/detail", params={
        "nodeId": node_id,
        "noticeId": item['noticeId'],
        "projectCode": item['projectCode'],
        "bizCode": item['tradingProcess'],
        "siteCode": item.get('regionCode', item['siteCode']),
        "version": item['edition'],
        "tradingType": item['noticeSecondType'],
    })
    resp.raise_for_status()
    data = resp.json()
    if data["errcode"] != 0:
        print(f"  ⚠️  详情接口错误: {data.get('errmsg')}")
        return None
    return data["data"]

def parse_detail(detail):
    """解析详情数据"""
    result = {
        "title": detail.get("title"),
        "publishDate": detail.get("publishDate"),
        "kv_info": {},
        "richtext": "",
    }

    for col in detail.get("tradingNoticeColumnModelList", []):
        if col.get("multiKeyValueTableList"):
            for table in col["multiKeyValueTableList"]:
                for kv in table:
                    result["kv_info"][kv["key"]] = kv.get("value")

        if col.get("richtext"):
            result["richtext"] = col["richtext"]

    return result

def extract_suppliers(html):
    """从HTML中提取供应商和价格信息"""
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    suppliers = []

    for table in soup.find_all('table'):
        # 查找表头
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        else:
            first_row = table.find('tr')
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]

        # 只处理包含"供应商"和"中标"或"成交"的表格（排除评分表）
        if not any('供应商' in h for h in headers):
            continue
        if not any('中标' in h or '成交' in h for h in headers):
            continue
        if any('得分' in h or '排名' in h for h in headers):
            continue  # 跳过评分表

        # 找到供应商和价格列的索引
        supplier_idx = None
        price_idx = None
        for i, h in enumerate(headers):
            if '供应商名称' in h or h == '供应商':
                supplier_idx = i
            if ('中标' in h or '成交' in h) and ('金额' in h or '价格' in h):
                price_idx = i

        if supplier_idx is None:
            continue

        # 提取数据行
        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else table.find_all('tr')[1:]

        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) > supplier_idx:
                supplier = cols[supplier_idx].get_text(strip=True)
                price = ''
                if price_idx is not None and len(cols) > price_idx:
                    price = cols[price_idx].get_text(strip=True)

                if supplier and supplier not in headers:
                    suppliers.append({
                        'supplier': supplier,
                        'price': price,
                    })

    return suppliers

def save_full_data(item, detail, project_code):
    """保存完整数据为JSON和Markdown"""
    # 保存JSON
    full_data = {
        "list_info": item,
        "detail": detail
    }
    json_file = f"{OUTPUT_DIR}/json/{project_code}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    # 保存Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0

    md_content = f"# {detail.get('title', '')}\n\n"
    md_content += f"**项目编号**: {project_code}\n\n"
    md_content += f"**发布时间**: {detail.get('publishDate', '')}\n\n"

    for col in detail.get('tradingNoticeColumnModelList', []):
        md_content += f"## {col.get('name', '')}\n\n"

        if col.get('multiKeyValueTableList'):
            for table in col['multiKeyValueTableList']:
                for kv in table:
                    md_content += f"- **{kv['key']}**: {kv.get('value', '')}\n"
            md_content += "\n"

        if col.get('richtext'):
            md_content += h.handle(col['richtext']) + "\n\n"

    md_file = f"{OUTPUT_DIR}/markdown/{project_code}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

def main():
    """主函数"""
    csv_file = f"{OUTPUT_DIR}/政府采购中标结果.csv"

    # 获取第一页数据
    page_data = get_items(page_no=1, page_size=10)
    print(f"总记录数: {page_data['total']}, 总页数: {page_data['pageTotal']}")

    # 先收集所有数据
    all_rows = []
    all_fields = set(['公告标题', '项目编号', '发布时间', '供应商名称', '中标价格'])

    for i, item in enumerate(page_data['pageData'], 1):
        print(f"[{i}] {item['noticeTitle']}")

        # 获取 nodeId
        node_list = get_node_list(item)
        node_id = find_node_id(item, node_list)
        if not node_id:
            print("  ⚠️  未找到 nodeId，跳过")
            continue

        detail = get_detail(item, node_id)
        if not detail:
            continue

        # 保存完整数据
        save_full_data(item, detail, item['projectCode'])

        parsed = parse_detail(detail)
        suppliers = extract_suppliers(parsed['richtext'])

        all_fields.update(parsed['kv_info'].keys())

        if suppliers:
            for sup in suppliers:
                row = {
                    '公告标题': parsed['title'],
                    '项目编号': item['projectCode'],
                    '发布时间': parsed['publishDate'],
                    '供应商名称': sup['supplier'],
                    '中标价格': sup['price'],
                }
                row.update(parsed['kv_info'])
                all_rows.append(row)
        else:
            row = {
                '公告标题': parsed['title'],
                '项目编号': item['projectCode'],
                '发布时间': parsed['publishDate'],
            }
            row.update(parsed['kv_info'])
            all_rows.append(row)

        time.sleep(0.5)

    # 写入CSV
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"\n✅ 数据已保存:")
    print(f"  - CSV: {csv_file}")
    print(f"  - JSON: {OUTPUT_DIR}/json/")
    print(f"  - Markdown: {OUTPUT_DIR}/markdown/")

if __name__ == "__main__":
    main()
