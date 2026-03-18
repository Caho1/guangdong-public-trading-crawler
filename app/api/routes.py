"""API 路由"""
import os
import json
import subprocess
import sys
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException
from app.services.crawler import crawler_service

router = APIRouter(prefix="/api", tags=["政府采购"])

DATA_DIR = "data/gov_procurement"


def parse_publish_date(value: str):
    """解析发布时间字符串为 datetime。"""
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def matches_publish_range(value: str, publish_range: str) -> bool:
    """判断发布时间是否命中范围筛选。"""
    if publish_range in ("", "all"):
        return True

    publish_date = parse_publish_date(value)
    if not publish_date:
        return False

    now = datetime.now()
    if publish_range == "today":
        return publish_date.date() == now.date()
    if publish_range == "7d":
        return publish_date >= now - timedelta(days=7)
    if publish_range == "30d":
        return publish_date >= now - timedelta(days=30)

    return True


@router.get("/items")
def list_items(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    keyword: str = Query("", description="搜索关键词")
):
    """获取中标结果公告列表（实时）"""
    data = crawler_service.get_items(page_no=page, page_size=size, keyword=keyword)
    if not data:
        raise HTTPException(status_code=500, detail="获取数据失败")

    return {
        "total": data['total'],
        "page": data['pageNo'],
        "size": data['pageSize'],
        "pages": data['pageTotal'],
        "items": data['pageData']
    }


@router.get("/items/{project_code}")
def get_item_detail(project_code: str):
    """获取单个项目详情（实时）"""
    data = crawler_service.get_items(page_no=1, page_size=10, keyword=project_code)
    if not data or not data['pageData']:
        raise HTTPException(status_code=404, detail="项目不存在")

    item = next((i for i in data['pageData'] if i['projectCode'] == project_code), None)
    if not item:
        raise HTTPException(status_code=404, detail="项目不存在")

    node_list = crawler_service.get_node_list(item)
    node_id = crawler_service.find_node_id(item, node_list)
    if not node_id:
        raise HTTPException(status_code=500, detail="无法获取项目详情")

    detail = crawler_service.get_detail(item, node_id)
    if not detail:
        raise HTTPException(status_code=500, detail="获取详情失败")

    return {
        "list_info": item,
        "detail": detail
    }


@router.post("/crawl")
def run_crawl(size: int = Query(10, ge=1, le=100, description="抓取条数")):
    """运行爬虫增量抓取数据"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.scripts.crawler", "--size", str(size)],
            capture_output=True, timeout=300, encoding="utf-8", errors="replace"
        )
        # 尝试从最后一行解析统计JSON
        stats = {}
        if result.stdout:
            for line in reversed(result.stdout.strip().splitlines()):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        stats = json.loads(line)
                    except json.JSONDecodeError:
                        pass
                    break
        if result.returncode == 0:
            return {"success": True, "message": "抓取完成", **stats}
        else:
            return {"success": False, "message": result.stderr[-500:] if result.stderr else "未知错误"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "抓取超时（5分钟）"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@router.get("/local/list")
def list_local_items(
    keyword: str = Query("", description="搜索关键词"),
    region: str = Query("", description="地区"),
    project_owner: str = Query("", description="采购单位"),
    publish_range: str = Query("all", description="发布时间范围"),
):
    """获取本地已爬取的数据列表"""
    json_dir = os.path.join(DATA_DIR, "json")
    if not os.path.isdir(json_dir):
        return {"items": [], "total": 0}

    items = []
    for fname in sorted(os.listdir(json_dir)):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(json_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)

        list_info = data.get("list_info", {})
        detail = data.get("detail", {})

        # 提取关键信息
        kv_info = {}
        for col in detail.get("tradingNoticeColumnModelList", []):
            if col.get("multiKeyValueTableList"):
                for table in col["multiKeyValueTableList"]:
                    for kv in table:
                        kv_info[kv["key"]] = kv.get("value", "")

        price = kv_info.get("中标 (成交) 价格", "")
        price_display = kv_info.get("中标优惠率或其它类型价格", "") or price
        unit = kv_info.get("价格单位", "")

        item = {
            "filename": fname.replace(".json", ""),
            "title": detail.get("title", list_info.get("noticeTitle", "")),
            "projectCode": list_info.get("projectCode", ""),
            "publishDate": detail.get("publishDate", ""),
            "regionName": list_info.get("regionName", ""),
            "projectOwner": list_info.get("projectOwner", ""),
            "projectName": kv_info.get("采购项目名称", ""),
            "price": price,
            "priceDisplay": price_display,
            "priceUnit": unit,
            "nature": kv_info.get("公告性质", ""),
        }

        if region and item["regionName"] != region:
            continue
        if project_owner and item["projectOwner"] != project_owner:
            continue
        if not matches_publish_range(item["publishDate"], publish_range):
            continue
        if keyword and keyword.lower() not in json.dumps(item, ensure_ascii=False).lower():
            continue
        items.append(item)

    return {"items": items, "total": len(items)}


@router.get("/local/markdown/{filename}")
def get_local_markdown(filename: str):
    """获取本地 Markdown 文件内容"""
    md_dir = os.path.join(DATA_DIR, "markdown")
    safe_name = os.path.basename(filename)
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    fpath = os.path.join(md_dir, safe_name)

    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="文件不存在")

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()

    return {"filename": safe_name, "content": content}
