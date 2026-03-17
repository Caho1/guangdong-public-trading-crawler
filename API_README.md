# 广东省政府采购中标结果 API

FastAPI 封装的政府采购中标结果查询接口。

## 安装依赖

```bash
uv pip install fastapi uvicorn requests
```

## 启动服务

```bash
# 方式1：直接运行
python api.py

# 方式2：使用 uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000

# 方式3：后台运行
nohup uvicorn api:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

## API 接口

### 1. 获取列表

**请求：**
```bash
GET /api/items?page=1&size=10&keyword=
```

**参数：**
- `page`: 页码（默认1）
- `size`: 每页数量（默认10，最大50）
- `keyword`: 搜索关键词（可选）

**响应示例：**
```json
{
  "total": "25988",
  "page": 1,
  "size": 10,
  "pages": 2599,
  "items": [...]
}
```

### 2. 获取详情

**请求：**
```bash
GET /api/items/{project_code}
```

**参数：**
- `project_code`: 项目编号

**响应示例：**
```json
{
  "list_info": {...},
  "detail": {...}
}
```

## 测试示例

```bash
# 获取列表
curl "http://localhost:8000/api/items?page=1&size=2"

# 获取详情
curl "http://localhost:8000/api/items/0724-2631YJ010633"

# 搜索
curl "http://localhost:8000/api/items?keyword=医院"
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
