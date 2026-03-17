#!/usr/bin/env python3
"""政府采购中标结果 API"""
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="广东省政府采购中标结果API", version="1.0.0")

BASE = "https://ygp.gdzwfw.gov.cn/ggzy-portal"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://ygp.gdzwfw.gov.cn/",
})

def get_items(page_no=1, page_size=10, keyword=""):
    """获取中标结果公告列表"""
    resp = session.post(f"{BASE}/search/v2/items", json={
        "type": "trading-type",
        "openConvert": False,
        "keyword": keyword,
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
    return data["data"] if data["errcode"] == 0 else None

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
    return data["data"] if data["errcode"] == 0 else []

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
    return data["data"] if data["errcode"] == 0 else None

@app.get("/")
def root():
    """API 根路径"""
    return {
        "message": "广东省政府采购中标结果API",
        "docs": "/docs",
        "endpoints": {
            "列表": "GET /api/items?page=1&size=10&keyword=",
            "详情": "GET /api/items/{project_code}"
        }
    }

@app.get("/api/items")
def list_items(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    keyword: str = Query("", description="搜索关键词")
):
    """获取中标结果公告列表"""
    data = get_items(page_no=page, page_size=size, keyword=keyword)
    if not data:
        return JSONResponse({"error": "获取数据失败"}, status_code=500)

    return {
        "total": data['total'],
        "page": data['pageNo'],
        "size": data['pageSize'],
        "pages": data['pageTotal'],
        "items": data['pageData']
    }

@app.get("/api/items/{project_code}")
def get_item_detail(project_code: str):
    """获取单个项目详情"""
    # 先搜索项目
    data = get_items(page_no=1, page_size=10, keyword=project_code)
    if not data or not data['pageData']:
        return JSONResponse({"error": "项目不存在"}, status_code=404)

    # 找到匹配的项目
    item = None
    for i in data['pageData']:
        if i['projectCode'] == project_code:
            item = i
            break

    if not item:
        return JSONResponse({"error": "项目不存在"}, status_code=404)

    # 获取详情
    node_list = get_node_list(item)
    node_id = find_node_id(item, node_list)
    if not node_id:
        return JSONResponse({"error": "无法获取项目详情"}, status_code=500)

    detail = get_detail(item, node_id)
    if not detail:
        return JSONResponse({"error": "获取详情失败"}, status_code=500)

    return {
        "list_info": item,
        "detail": detail
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
