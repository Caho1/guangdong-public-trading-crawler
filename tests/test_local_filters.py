import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api import routes
from app.main import app


def build_item(title, code, region, owner, publish_date):
    return {
        "list_info": {
            "noticeTitle": title,
            "projectCode": code,
            "regionName": region,
            "projectOwner": owner,
        },
        "detail": {
            "title": title,
            "publishDate": publish_date,
            "tradingNoticeColumnModelList": [],
        },
    }


class LocalListFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        json_dir = Path(self.temp_dir.name) / "json"
        json_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        items = [
            (
                "guangzhou.json",
                build_item(
                    "广州项目公告",
                    "GZ-001",
                    "广州市",
                    "广州采购单位",
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            ),
            (
                "foshan.json",
                build_item(
                    "佛山项目公告",
                    "FS-001",
                    "佛山市",
                    "佛山采购单位",
                    (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            ),
            (
                "zhuhai.json",
                build_item(
                    "珠海项目公告",
                    "ZH-001",
                    "珠海市",
                    "珠海采购单位",
                    (now - timedelta(days=40)).strftime("%Y-%m-%d %H:%M:%S"),
                ),
            ),
        ]

        for filename, payload in items:
            with open(json_dir / filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)

        self.data_dir_patch = patch.object(routes, "DATA_DIR", self.temp_dir.name)
        self.data_dir_patch.start()

    def tearDown(self):
        self.data_dir_patch.stop()
        self.temp_dir.cleanup()

    def test_filters_by_region(self):
        response = self.client.get("/api/local/list", params={"region": "广州市"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["projectCode"], "GZ-001")

    def test_filters_by_project_owner(self):
        response = self.client.get("/api/local/list", params={"project_owner": "佛山采购单位"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["projectCode"], "FS-001")

    def test_filters_by_publish_range(self):
        response = self.client.get("/api/local/list", params={"publish_range": "7d"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        project_codes = sorted(item["projectCode"] for item in data["items"])
        self.assertEqual(project_codes, ["FS-001", "GZ-001"])

    def test_combines_keyword_and_filters(self):
        response = self.client.get(
            "/api/local/list",
            params={
                "keyword": "项目",
                "region": "广州市",
                "project_owner": "广州采购单位",
                "publish_range": "today",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["projectCode"], "GZ-001")

    def test_home_page_contains_local_filter_controls(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn('id="region-filter"', html)
        self.assertIn('id="owner-filter"', html)
        self.assertIn('id="publish-filter"', html)
        self.assertIn('id="filter-apply-btn"', html)

    def test_filter_button_uses_safe_two_column_layout(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertNotIn('xl:grid-cols-[1fr_1fr_1fr_auto]', html)
        self.assertIn('sm:col-span-2', html)
