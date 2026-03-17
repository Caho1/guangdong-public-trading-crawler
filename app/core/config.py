"""应用配置"""

BASE_URL = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
}

# 政府采购配置
GOV_PROCUREMENT_CONFIG = {
    "siteCode": "44",
    "secondType": "D",
    "tradingProcess": "553,3871,2871,2873",
}
