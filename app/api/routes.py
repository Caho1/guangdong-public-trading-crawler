"""API 路由"""
from fastapi import APIRouter, Query, HTTPException
from app.services.crawler import crawler_service

router = APIRouter(prefix="/api", tags=["政府采购"])


@router.get("/items")
def list_items(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    keyword: str = Query("", description="搜索关键词")
):
    """获取中标结果公告列表"""
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
    """获取单个项目详情"""
    # 搜索项目
    data = crawler_service.get_items(page_no=1, page_size=10, keyword=project_code)
    if not data or not data['pageData']:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 找到匹配的项目
    item = next((i for i in data['pageData'] if i['projectCode'] == project_code), None)
    if not item:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 获取详情
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
