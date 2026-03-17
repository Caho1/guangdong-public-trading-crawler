"""爬虫服务"""
import requests
from app.core.config import BASE_URL, HEADERS, GOV_PROCUREMENT_CONFIG


class CrawlerService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def get_items(self, page_no=1, page_size=10, keyword=""):
        """获取中标结果公告列表"""
        resp = self.session.post(f"{BASE_URL}/search/v2/items", json={
            "type": "trading-type",
            "openConvert": False,
            "keyword": keyword,
            **GOV_PROCUREMENT_CONFIG,
            "thirdType": "[]",
            "projectType": "",
            "publishStartTime": "",
            "publishEndTime": "",
            "pageNo": page_no,
            "pageSize": page_size,
        })
        resp.raise_for_status()
        data = resp.json()
        return data["data"] if data["errcode"] == 0 else None

    def get_node_list(self, item):
        """获取项目节点列表"""
        resp = self.session.get(f"{BASE_URL}/center/apis/trading-notice/new/nodeList", params={
            "siteCode": item.get('regionCode', item['siteCode']),
            "tradingType": item['noticeSecondType'],
            "bizCode": item['tradingProcess'],
            "projectCode": item['projectCode'],
            "classify": item.get('projectType', ''),
        })
        resp.raise_for_status()
        data = resp.json()
        return data["data"] if data["errcode"] == 0 else []

    def find_node_id(self, item, node_list):
        """从节点列表中匹配 nodeId"""
        for node in node_list:
            if node.get("selectedBizCode") == item["tradingProcess"]:
                return node["nodeId"]
        for node in node_list:
            if node.get("dataCount", 0) > 0:
                return node["nodeId"]
        return None

    def get_detail(self, item, node_id):
        """获取公告详情"""
        resp = self.session.get(f"{BASE_URL}/center/apis/trading-notice/new/detail", params={
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
        return data["data"] if data["errcode"] == 0 else None


crawler_service = CrawlerService()
