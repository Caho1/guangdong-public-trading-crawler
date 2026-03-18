#!/usr/bin/env python3
"""政府采购-中标结果公告爬虫（异步并发 + 阿里云FC代理池）"""
import asyncio
import csv
import json
import os
import random
import time
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup
import html2text

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"
OUTPUT_DIR = "data/gov_procurement"

# 阿里云FC代理池
PROXY_LIST = [
    "https://spider-proxy-fmggmraknx.cn-hangzhou.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-beijing.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-shanghai.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-zhangjiakou.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-shenzhen.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-qingdao.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-chengdu.fcapp.run",
    "https://spider-proxy-fmggmraknx.cn-huhehaote.fcapp.run",
]
USE_PROXY = True
CONCURRENCY = len(PROXY_LIST)  # 并发数 = 代理节点数

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
}

# 创建输出目录
os.makedirs(f"{OUTPUT_DIR}/json", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/markdown", exist_ok=True)


# ==================== 异步 HTTP ====================

async def proxy_request(session, method, url, **kwargs):
    """通过FC代理池发送异步请求，自动轮换IP"""
    if USE_PROXY:
        proxy = random.choice(PROXY_LIST)
        params = kwargs.pop("params", None)
        if params:
            url = f"{url}?{urlencode(params)}"
        headers = kwargs.pop("headers", {})
        headers.update(DEFAULT_HEADERS)
        headers["Proxytourl"] = url
        headers["Accept-Encoding"] = "identity"
        kwargs["headers"] = headers
        target = proxy
    else:
        headers = kwargs.pop("headers", {})
        headers.update(DEFAULT_HEADERS)
        kwargs["headers"] = headers
        kwargs["ssl"] = False
        target = url

    async with session.request(method, target, **kwargs) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def get_items(session, page_no=1, page_size=10):
    """获取中标结果公告列表"""
    data = await proxy_request(session, "POST", f"{BASE}/search/v2/items", json={
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
    assert data["errcode"] == 0
    return data["data"]


async def fetch_item_detail(session, item):
    """获取单个项目的完整详情（nodeList + detail）"""
    # 1. 获取 nodeList
    node_data = await proxy_request(session, "GET", f"{BASE}/center/apis/trading-notice/new/nodeList", params={
        "siteCode": item.get('regionCode', item['siteCode']),
        "tradingType": item['noticeSecondType'],
        "bizCode": item['tradingProcess'],
        "projectCode": item['projectCode'],
        "classify": item.get('projectType', ''),
    })
    if node_data["errcode"] != 0:
        return None
    node_list = node_data["data"]

    # 2. 找 nodeId
    node_id = None
    for node in node_list:
        if node.get("selectedBizCode") == item["tradingProcess"]:
            node_id = node["nodeId"]
            break
    if not node_id:
        for node in node_list:
            if node.get("dataCount", 0) > 0:
                node_id = node["nodeId"]
                break
    if not node_id:
        return None

    # 3. 获取详情
    detail_data = await proxy_request(session, "GET", f"{BASE}/center/apis/trading-notice/new/detail", params={
        "nodeId": node_id,
        "noticeId": item['noticeId'],
        "projectCode": item['projectCode'],
        "bizCode": item['tradingProcess'],
        "siteCode": item.get('regionCode', item['siteCode']),
        "version": item['edition'],
        "tradingType": item['noticeSecondType'],
    })
    if detail_data["errcode"] != 0:
        return None
    return detail_data["data"]


# ==================== 解析 & 保存（同步，CPU密集） ====================

def parse_detail(detail):
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
    if not html:
        return []
    soup = BeautifulSoup(html, 'html.parser')
    suppliers = []
    for table in soup.find_all('table'):
        headers = []
        header_row = table.find('thead')
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        else:
            first_row = table.find('tr')
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]
        if not any('供应商' in h for h in headers):
            continue
        if not any('中标' in h or '成交' in h for h in headers):
            continue
        if any('得分' in h or '排名' in h for h in headers):
            continue
        supplier_idx = None
        price_idx = None
        for i, h in enumerate(headers):
            if '供应商名称' in h or h == '供应商':
                supplier_idx = i
            if ('中标' in h or '成交' in h) and ('金额' in h or '价格' in h):
                price_idx = i
        if supplier_idx is None:
            continue
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
                    suppliers.append({'supplier': supplier, 'price': price})
    return suppliers


def sanitize_filename(name):
    for char in '<>:"/\\|?*':
        name = name.replace(char, '_')
    return name.strip()


def save_full_data(item, detail, project_name, project_code):
    safe_name = sanitize_filename(project_name)
    filename = f"{safe_name}_{project_code}"

    # JSON
    full_data = {"list_info": item, "detail": detail}
    with open(f"{OUTPUT_DIR}/json/{filename}.json", 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

    # Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0
    md = f"# {detail.get('title', '')}\n\n"
    md += f"**项目编号**: {project_code}\n\n"
    md += f"**发布时间**: {detail.get('publishDate', '')}\n\n"
    for col in detail.get('tradingNoticeColumnModelList', []):
        md += f"## {col.get('name', '')}\n\n"
        if col.get('multiKeyValueTableList'):
            for table in col['multiKeyValueTableList']:
                for kv in table:
                    md += f"- **{kv['key']}**: {kv.get('value', '')}\n"
            md += "\n"
        if col.get('richtext'):
            md += h.handle(col['richtext']) + "\n\n"
    with open(f"{OUTPUT_DIR}/markdown/{filename}.md", 'w', encoding='utf-8') as f:
        f.write(md)


def get_existing_project_codes():
    json_dir = f"{OUTPUT_DIR}/json"
    if not os.path.isdir(json_dir):
        return set()
    codes = set()
    for fname in os.listdir(json_dir):
        if fname.endswith(".json"):
            code = fname.rsplit("_", 1)[-1].replace(".json", "")
            codes.add(code)
    return codes


def rebuild_csv():
    json_dir = f"{OUTPUT_DIR}/json"
    csv_file = f"{OUTPUT_DIR}/政府采购中标结果.csv"
    if not os.path.isdir(json_dir):
        return
    all_rows = []
    all_fields = set(['公告标题', '项目编号', '发布时间', '供应商名称', '中标价格'])
    for fname in sorted(os.listdir(json_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(json_dir, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        item = data.get("list_info", {})
        detail = data.get("detail", {})
        parsed = parse_detail(detail)
        suppliers = extract_suppliers(parsed['richtext'])
        all_fields.update(parsed['kv_info'].keys())
        if suppliers:
            for sup in suppliers:
                row = {'公告标题': parsed['title'], '项目编号': item.get('projectCode', ''), '发布时间': parsed['publishDate'], '供应商名称': sup['supplier'], '中标价格': sup['price']}
                row.update(parsed['kv_info'])
                all_rows.append(row)
        else:
            row = {'公告标题': parsed['title'], '项目编号': item.get('projectCode', ''), '发布时间': parsed['publishDate']}
            row.update(parsed['kv_info'])
            all_rows.append(row)
    with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)


# ==================== 并发工作器 ====================

async def process_item(session, sem, item, existing_codes, results):
    """处理单个项目（受信号量控制并发）"""
    project_code = item['projectCode']
    if project_code in existing_codes:
        results['skipped'] += 1
        print(f"  [SKIP] {item['noticeTitle']}")
        return

    async with sem:
        proxy_used = random.choice(PROXY_LIST).split('.')[-3].split('-')[-1] if USE_PROXY else "direct"
        print(f"  [FETCH] {item['noticeTitle']}  <- {proxy_used}")
        try:
            detail = await fetch_item_detail(session, item)
            if not detail:
                print(f"    [WARN] 获取详情失败，跳过")
                results['failed'] += 1
                return

            parsed = parse_detail(detail)
            project_name = parsed['kv_info'].get('采购项目名称', item['noticeTitle'])
            save_full_data(item, detail, project_name, project_code)
            existing_codes.add(project_code)
            results['new'] += 1
            print(f"    [OK] 已保存 ({results['new']} new)")
        except Exception as e:
            print(f"    [ERR] {e}")
            results['failed'] += 1


async def main(page_size=10):
    """主函数（异步并发增量抓取）"""
    existing_codes = get_existing_project_codes()
    print(f"[INFO] 本地已有 {len(existing_codes)} 条数据")
    print(f"[INFO] 目标抓取 {page_size} 条新数据，并发数: {CONCURRENCY}")

    t0 = time.time()
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY * 2, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=connector, trust_env=False) as session:
        # 收集待处理的新项目
        new_items = []
        page_no = 1
        max_pages = (page_size // 10) + 10  # 预估需要翻的页数

        while len(new_items) < page_size and page_no <= max_pages:
            fetch_size = min(page_size, 50)  # 每页最多拉50条，减少翻页次数
            page_data = await get_items(session, page_no=page_no, page_size=fetch_size)
            if page_no == 1:
                print(f"[INFO] 平台总记录数: {page_data['total']}")

            page_items = page_data.get('pageData', [])
            if not page_items:
                print(f"[INFO] 第{page_no}页无数据，已到末尾")
                break

            page_new = 0
            page_skip = 0
            for item in page_items:
                if item['projectCode'] not in existing_codes:
                    new_items.append(item)
                    page_new += 1
                    if len(new_items) >= page_size:
                        break
                else:
                    page_skip += 1

            print(f"[INFO] 第{page_no}页: {page_new} 条新数据, {page_skip} 条已有")
            page_no += 1

        if not new_items:
            print(f"[INFO] 没有新数据需要抓取")
        else:
            print(f"[INFO] 找到 {len(new_items)} 条新数据，开始并发抓取...")

            results = {'new': 0, 'skipped': 0, 'failed': 0}
            tasks = [process_item(session, sem, item, existing_codes, results) for item in new_items]
            await asyncio.gather(*tasks)

    # 重建CSV
    rebuild_csv()

    elapsed = time.time() - t0
    total = len(existing_codes)
    new_count = len(new_items) if new_items else 0
    skipped = len(get_existing_project_codes()) - (total - new_count) if new_items else 0

    # 统计实际结果
    actual_results = {'new': 0, 'skipped': 0, 'failed': 0}
    if new_items:
        actual_results = results

    print(f"\n[OK] 抓取完成 ({elapsed:.1f}s)")
    print(f"  新增: {actual_results['new']}  失败: {actual_results['failed']}  本地共: {total + actual_results['new']} 条")
    print(json.dumps({"new": actual_results['new'], "skipped": actual_results['skipped'], "failed": actual_results['failed'], "total": len(get_existing_project_codes())}, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=10, help="抓取条数")
    args = parser.parse_args()
    asyncio.run(main(page_size=args.size))
