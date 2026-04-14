# Code Standards

**Applies to all code (backend, frontend, analytics, and AI)**
**Goal:** Ensure readability, speed, and uniformity across all codebases.

---

##  1. General Principles

1. **Readability over cleverness** — code should be self-explanatory to new developers.
2. **Simplicity first** — avoid abstractions until repetition happens 3+ times.
3. **Consistency > Individual preference** — all code follows the same shape and naming.
4. **Documentation by default** — each function and module must explain *why* it exists.
5. **Data-driven mindset** — every module should be measurable or testable.
6. **Functions are verbs** — they *do* something. Example: `load_data()`, `train_model()`, `analyze_metrics()`.
7. **No hidden state** — all state passed explicitly via parameters or clear class attributes.
8. **Automate formatting + linting** — developers shouldn’t argue about style.

---

##  2. Naming Conventions

### Functions and Variables

* **Style:** `snake_case`

* ✅ Example:

  ```python
  def load_customer_data():
      ...
  ```

* ❌ Avoid:

  * `loadCustomerData()`
  * `LoadCustomerData()`
  * `Load_Customer_Data()`

### Classes

* **Style:** `PascalCase`

  ```python
  class DataAnalyzer:
      ...
  ```

### Constants

* **Style:** `ALL_CAPS_WITH_UNDERSCORES`

  ```python
  MAX_RETRIES = 3
  ```

### Files and Modules

* **Style:** `lowercase_with_underscores.py`

  * ✅ Example: `data_loader.py`, `api_routes.py`
  * ❌ Avoid: `DataLoader.py`, `dataLoader.py`

### Project Directory Example

```
/src
  /core
    __init__.py
    data_loader.py
    analytics_engine.py
  /ai
    model_trainer.py
    predictor.py
  /api
    app.py
    routes.py
  /tests
    test_data_loader.py
```

---

##  3. Function Structure Template

Every function must:

1. Be small — aim for ≤ 30 lines.
2. Have a docstring explaining **what, inputs, outputs, and side effects**.
3. Return values explicitly (no silent prints unless for logs).

```python
def new_func(input_data: dict, config: dict = None) -> dict:
    """
    Short description (1 line).

    Args:
        input_data (dict): Incoming data payload.
        config (dict, optional): Configuration overrides.

    Returns:
        dict: Processed and validated output.

    Example:
        result = new_func({"a": 1})
    """
    # Validate input
    if not input_data:
        raise ValueError("input_data cannot be empty")

    # Main logic
    processed = {k: v * 2 for k, v in input_data.items()}

    return processed
```

---

##  4. Commenting & Documentation Rules

* Write comments that explain *why*, not *what*.
* Always add a **module docstring** at the top of files.
* Use `# TODO:` and `# NOTE:` consistently.
* Example:

  ```python
  """
  analytics_engine.py
  --------------------
  Contains logic for computing key metrics.
  """

  # TODO: Add support for weekly aggregation
  def compute_growth_rate(customers, period):
      """Compute growth rate for the given time period."""
      ...
  ```

---

##  5. Testing Standards

* Each core function should have a matching test.
* Use **pytest**.
* Test naming: `test_<function_name>()`
* Example:

  ```python
  def test_new_func_returns_expected_result():
      data = {"a": 1}
      result = new_func(data)
      assert result == {"a": 2}
  ```

---

##  6. AI / Data / Analytics Code Rules

### Data Pipelines

* Separate **ETL**, **analytics**, and **ML** stages.
* Never mutate input data; always return a copy.

### ML Functions

* Naming examples:

  * `train_model()`
  * `evaluate_model()`
  * `predict_outcome()`
* Always log metrics to a central logger (not print).

### Analytics

* Use `analyze_` prefix for analytics-related functions.

  ```python
  def analyze_customer_retention(data):
      ...
  ```

---

##  7. API / Backend Standards

### Endpoints

* Use verbs for REST routes:

  * `POST /add_patient`
  * `GET /get_analytics`
* Each endpoint = controller + service separation:

  ```python
  # routes.py
  @app.route("/analyze", methods=["POST"])
  def analyze():
      return jsonify(analyze_request(request.json))
  ```

  ```python
  # services/analytics_service.py
  def analyze_request(payload):
      ...
  ```

### JSON Responses

* Always return:

  ```json
  { "status": "success", "data": {...}, "message": "" }
  ```

---

##  8. Tooling Setup

Use the following setup in all repos:

| Tool           | Purpose             | Config File               |
| -------------- | ------------------- | ------------------------- |
| **Black**      | Code formatter      | `pyproject.toml`          |
| **isort**      | Import sorting      | `pyproject.toml`          |
| **flake8**     | Linting             | `.flake8`                 |
| **pytest**     | Testing             | `pytest.ini`              |
| **pre-commit** | Auto enforce checks | `.pre-commit-config.yaml` |

### Example `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 24.8.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
```

---

##  9. Commit Message Convention

Follow **Conventional Commits**:

```
<type>(scope): short summary
```

Example:

```
feat(api): add analytics endpoint
fix(data): correct null handling in ETL
refactor(ai): improve training loop speed
```

---

##  10. Quick Summary Reference

| Type     | Example                                   |
| -------- | ----------------------------------------- |
| Function | `load_data()`, `analyze_trends()`         |
| Variable | `customer_count`, `daily_stats`           |
| Class    | `AnalyticsEngine`, `DataLoader`           |
| Constant | `DEFAULT_LIMIT`, `MAX_RETRIES`            |
| File     | `data_loader.py`, `ai_trainer.py`         |
| Test     | `test_analyze_trends.py`                  |
| Commit   | `feat(api): add route for trend analysis` |
