# 广东省公共资源交易平台爬虫

广东省公共资源交易平台数据采集工具，支持政府采购中标结果数据爬取和 API 查询。

## 项目结构

```
├── app/                    # FastAPI 应用
│   ├── main.py            # 应用入口
│   ├── api/               # API 路由层
│   ├── services/          # 业务逻辑层
│   ├── core/              # 配置管理
│   └── scripts/           # 爬虫脚本
├── tests/                 # 测试文件
├── data/                  # 数据目录（不提交到 git）
└── .gitignore
```

## 功能特性

### 1. 数据爬取
- 支持政府采购中标结果公告爬取
- 保存三种格式：JSON（原始数据）、Markdown（易读）、CSV（结构化）
- 文件命名使用项目名称，便于识别

### 2. API 接口
- RESTful API 接口
- 支持列表查询（分页、搜索）
- 支持详情查询
- 自动生成 API 文档

## 快速开始

### 安装依赖

```bash
uv pip install fastapi uvicorn requests beautifulsoup4 html2text
```

### 启动 API 服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

访问 API 文档：http://localhost:8000/docs

### 运行爬虫

```bash
python -m app.scripts.crawler
```

## API 使用

### 获取列表
```bash
GET /api/items?page=1&size=10&keyword=
```

### 获取详情
```bash
GET /api/items/{project_code}
```

## License

MIT
