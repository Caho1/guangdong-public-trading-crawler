import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.trust_env = False
retry_strategy = Retry(total=3, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)

# 测试附件信息
attachment = {
    "fileName": "评标报告（公示）.pdf",
    "rowGuid": "a6ddd752-6be3-48bf-9335-8b7bc2e0c20a-d5e859d3-eebf-4b91-ba77-5742ffaf56fe",
    "flowId": "1611478",
    "version": "v1"
}

# 尝试不同的下载URL组合
test_urls = [
    f"{BASE}/mhyy/config/cms/download/{attachment['rowGuid']}",
    f"{BASE}/mhyy/config/cms/download/{attachment['rowGuid']}?version={attachment['version']}",
    f"{BASE}/mhyy/config/cms/download?rowGuid={attachment['rowGuid']}",
    f"{BASE}/mhyy/config/cms/download?id={attachment['rowGuid']}",
    f"{BASE}/center/file/download/{attachment['rowGuid']}",
    f"{BASE}/file/download/{attachment['rowGuid']}",
]

print("测试不同的下载URL格式：\n")
for i, url in enumerate(test_urls, 1):
    print(f"[{i}] {url}")
    try:
        resp = session.get(url, timeout=10)
        print(f"    状态码: {resp.status_code}")
        print(f"    Content-Type: {resp.headers.get('Content-Type', 'N/A')}")

        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                print(f"    ✅ 可能成功! 内容长度: {len(resp.content)} 字节")
                with open(f"/Users/bystanders/Desktop/公共资源交易/downloads/test_{i}.pdf", 'wb') as f:
                    f.write(resp.content)
                break
            else:
                print(f"    返回JSON: {resp.text[:100]}")
        else:
            print(f"    响应: {resp.text[:100]}")
    except Exception as e:
        print(f"    错误: {e}")
    print()
