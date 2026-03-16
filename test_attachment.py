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

def download_attachment(attachment_obj, file_name):
    """下载附件 - 尝试多种URL格式"""
    row_guid = attachment_obj.get('rowGuid')
    flow_id = attachment_obj.get('flowId')

    # 尝试方式1: 使用rowGuid
    urls = [
        f"{BASE}/mhyy/config/cms/download/{row_guid}",
        f"{BASE}/mhyy/config/cms/download/{row_guid}?online=1",
        f"{BASE}/center/apis/file/download?rowGuid={row_guid}",
        f"{BASE}/center/apis/file/download?id={row_guid}",
    ]

    if flow_id:
        urls.append(f"{BASE}/mhyy/config/cms/download/{flow_id}")

    for url in urls:
        try:
            print(f"  尝试: {url}")
            resp = safe_request(session.get, url, stream=True)

            # 检查是否是JSON错误响应
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                print(f"  返回JSON: {resp.text[:100]}")
                continue

            # 保存文件
            save_path = f"/Users/bystanders/Desktop/公共资源交易/downloads/{file_name}"
            with open(save_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            return save_path, url
        except Exception as e:
            print(f"  失败: {e}")
            continue

    return None, None

if __name__ == "__main__":
    print("查找有附件的项目（查找多个）...\n")

    found_count = 0
    for page in range(1, 10):
        data = get_items(page_no=page)

        for item in data["pageData"]:
            node_id = get_node_id(item)
            if not node_id:
                continue

            detail = get_detail(item, node_id)

            for col in detail.get("tradingNoticeColumnModelList", []):
                files = col.get("noticeFileBOList", [])
                if files:
                    found_count += 1
                    print(f"[{found_count}] {item['noticeTitle'][:50]}...")
                    print(f"附件数量: {len(files)}")

                    for f in files[:1]:
                        print(f"附件: {f}\n")

                        try:
                            path, success_url = download_attachment(f, f['fileName'])
                            if path:
                                print(f"✅ 下载成功: {path}")
                                print(f"✅ URL: {success_url}\n")
                                exit(0)
                            else:
                                print(f"❌ 下载失败\n")
                        except Exception as e:
                            print(f"❌ 异常: {e}\n")

                    if found_count >= 5:
                        print("已测试5个附件，全部失败")
                        exit(1)

            time.sleep(0.5)

    print(f"共找到 {found_count} 个有附件的项目")
