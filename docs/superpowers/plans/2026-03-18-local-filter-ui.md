# Local Filter UI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three visible filters and a confirm button to the local data page without changing the existing list-detail layout.

**Architecture:** Extend `GET /api/local/list` with minimal query filtering, keep the HTML page as the only frontend surface, and derive dropdown options from the loaded local dataset. Apply TDD to the backend filtering first, then wire the frontend controls to the updated endpoint.

**Tech Stack:** FastAPI, static HTML + vanilla JavaScript, pytest/TestClient

---

## Chunk 1: Backend Filtering

### Task 1: Add regression tests for local list filtering

**Files:**
- Modify: `tests/test_gov_procurement.py`
- Test: `tests/test_gov_procurement.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_local_list_filters_by_region(...):
    ...

def test_local_list_filters_by_project_owner(...):
    ...

def test_local_list_filters_by_publish_range(...):
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gov_procurement.py -q`
Expected: FAIL because `/api/local/list` does not yet accept or apply the new filters.

- [ ] **Step 3: Write minimal implementation**

```python
@router.get("/local/list")
def list_local_items(..., region: str = "", project_owner: str = "", publish_range: str = "all"):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gov_procurement.py -q`
Expected: PASS for the new filtering cases.

## Chunk 2: Frontend Controls

### Task 2: Add three dropdowns and a confirm button

**Files:**
- Modify: `app/static/index.html`

- [ ] **Step 1: Add the failing behavior target**

Document the expected control IDs and the request shape used by the page:
- `region-filter`
- `owner-filter`
- `publish-filter`
- `filter-apply-btn`

- [ ] **Step 2: Implement the minimal HTML and JS changes**

```html
<select id="region-filter"></select>
<select id="owner-filter"></select>
<select id="publish-filter"></select>
<button id="filter-apply-btn">确定</button>
```

- [ ] **Step 3: Update data loading flow**

Use the selected values when calling `/api/local/list` and populate region / owner dropdowns from returned items.

- [ ] **Step 4: Run verification**

Run the backend and manually verify:
- local page renders the filters
- clicking `确定` refreshes the local list
- remote tab remains usable

## Chunk 3: Final Verification

### Task 3: Run the full verification pass

**Files:**
- Verify only

- [ ] **Step 1: Run automated tests**

Run: `pytest tests/test_gov_procurement.py -q`

- [ ] **Step 2: Run a manual smoke check**

Run the app and verify:
- `http://localhost:8000/` loads
- local filters appear below the search box
- each filter changes local results when combined with search

