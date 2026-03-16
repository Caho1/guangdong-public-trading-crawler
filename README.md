# 广东省公共资源交易平台爬虫

广东省公共资源交易平台数据采集工具，支持获取招标公告、详情信息、价格数据和附件下载。

## 功能特性

- ✅ 获取招标项目列表
- ✅ 获取项目详情和结构化数据
- ✅ 解析HTML内容提取价格信息
- ✅ 下载附件文件（PDF等）
- ✅ 导出数据到CSV

## 安装

使用 uv 创建虚拟环境并安装依赖：

```bash
uv venv
source .venv/bin/activate
uv pip install requests beautifulsoup4 lxml
```

## 使用示例

### 1. 基础爬取测试

```bash
python crawler.py
```

### 2. 提取价格信息

```bash
python extract_prices.py
```

### 3. 导出完整数据到CSV

```bash
python export_full_data.py
```

### 4. 测试附件下载

```bash
python test_correct_download.py
```

## 接口说明

### 列表接口
```
POST /ggzy-portal/search/v2/items
```

### 节点列表接口
```
GET /ggzy-portal/center/apis/trading-notice/new/nodeList
```

### 详情接口
```
GET /ggzy-portal/center/apis/trading-notice/new/detail
```

### 附件下载接口
```
GET /ggzy-portal/base/sys-file/download/{edition}/{rowGuid}?{flowId}
```

## 注意事项

- 请求间隔建议 0.5-1 秒，避免触发限流
- pageSize 最大为 10
- 附件下载需要使用正确的 edition 参数（通常为 v3）

## License

MIT
