import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.trust_env = False
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
})
retry_strategy = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# 测试数据（从之前的测试中获取）
test_file = {
    "fileName": "评标报告（公示）.pdf",
    "rowGuid": "a6ddd752-6be3-48bf-9335-8b7bc2e0c20a-d5e859d3-eebf-4b91-ba77-5742ffaf56fe",
    "flowId": "1611478",
    "edition": "v3"
}

print("测试正确的附件下载接口...\n")

# 1. 获取文件大小
size_url = f"{BASE}/base/sys-file/download/size/{test_file['edition']}/{test_file['rowGuid']}?{test_file['flowId']}"
print(f"获取文件大小: {size_url}")
resp = session.get(size_url)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text[:200]}\n")

if resp.status_code == 200:
    # 2. 下载文件
    download_url = f"{BASE}/base/sys-file/download/{test_file['edition']}/{test_file['rowGuid']}?{test_file['flowId']}"
    print(f"下载文件: {download_url}")
    resp = session.get(download_url, stream=True)
    print(f"状态码: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type')}")

    if 'application/json' not in resp.headers.get('Content-Type', ''):
        save_path = f"/Users/bystanders/Desktop/公共资源交易/downloads/{test_file['fileName']}"
        with open(save_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ 下载成功: {save_path}")
    else:
        print(f"❌ 返回JSON: {resp.text[:200]}")
