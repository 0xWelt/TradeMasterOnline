# Agent Guidelines

## 环境准备

```bash
git clone git@github.com:0xWelt/TradeMasterOnline.git
cd TradeMasterOnline
uv sync --extra dev
source .venv/bin/activate   # Linux/macOS
pre-commit install
```

**始终先激活虚拟环境再运行命令**：

```bash
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

激活后可直接运行 `python`、`pytest`、`pre-commit` 等命令，无需 `uv run` 前缀。

---

## 工作流

任何非平凡改动必须遵循以下流程：

```
用户提出需求
    │
    ▼
是否需要调研？ ──是──→ 使用 deep-survey skill 生成 Survey
    │                          │
    否                         ▼
    │                    docs/survey/YYYY-MM-DD_<topic>.md
    ▼                          │
手写 Plan 文档 ←───────────────┘
    │
    ▼
提交给用户 review → 获批
    │
    ▼
按 Plan 实施代码
    │
    ▼
测试验证（pytest + pre-commit）
    │
    ▼
同步更新 Manual
```

### Plan 是手写文档

Plan 是写到 `docs/plan/YYYY-MM-DD_<brief_description>.md` 的 **Markdown 文件**，不是用工具内置的 PlanMode。内容包括：目标与范围、架构变更、详细设计、测试策略、实现状态（checklist）。

是否需要 plan 由用户说明。通常大 feature、架构重构、涉及多文件的修改需要 plan；简单需求可直接实施。

---

## 代码规范

### pre-commit

提交前运行（**必须先激活虚拟环境**）：

```bash
source .venv/bin/activate
pre-commit run --all-files
```

包含 **ruff**（格式化与 lint）和 **ty**（类型检查）。

**ty 类型检查注意事项**：

- 优先通过正确的类型注解、返回值标注和类型窄化消除类型错误。
- **禁止**在工作代码中使用 `typing.cast` 掩盖类型问题；`cast` 只允许在测试文件的 Mock 场景中使用。
- 若类型检查器因容器型变（如 `list` 的 invariant）报错，优先考虑将函数参数改为 `Sequence`、`Mapping` 等协变抽象基类，而非使用 `cast`。
- 必须通过注释忽略类型错误时，**使用 ty 原生格式**：`# ty: ignore[invalid-assignment]`（不是 `type: ignore`）。

> 项目已启用 `unused-type-ignore-comment = "error"`，未使用的 `# ty: ignore[...]` 会导致 CI 失败。

### pytest

新增功能或修改核心逻辑时，必须在 `tests/` 下提供对应的 pytest 单元测试。测试文件应与被测源文件一一对应：

| 源文件 | 测试文件 |
|--------|----------|
| `tmo/core/order.py` | `tests/tmo/core/test_order.py` |
| `tmo/env/trading_env.py` | `tests/tmo/env/test_trading_env.py` |

```bash
source .venv/bin/activate

# 运行测试
pytest -n auto --import-mode=importlib

# 带覆盖率
pytest -n auto --import-mode=importlib --cov --cov-report=term-missing
```

### 文档风格

**StrEnum / Pydantic 模型字段**：每个字段下方用三引号独立注释，class 底下不需要 `Attributes` 段落。字段之间无需空行，因为注释已经充当了间隔。

```python
class Side(StrEnum):
    """交易方向枚举。"""

    HOLD = 'HOLD'
    """观望（不下单）。"""
    BUY = 'BUY'
    """买入。"""
```

**其他类的 attribute**：不要用三引号注释，用普通 `#` 按需注释，放在行尾；注释过长时放在 attribute 的上方。

```python
class OrderManager:
    def __init__(self, books: dict[str, OrderBook]) -> None:
        self._books = books
        self._conditional_orders: list[Order] = []  # 未触发的条件单列表
        self._oco_groups: dict[str, list[str]] = {}  # OCO 组合：group_id -> [order_id, ...]
```

---

## 文档体系

项目文档统一放在 `docs/` 下，分三类：

| 类别 | 位置 | 说明 | 更新时机 |
|------|------|------|----------|
| **Survey** | `docs/survey/` | 使用 deep-survey skill 生成的深度调研报告 | 用户要求调研时生成 |
| **Plan** | `docs/plan/` | 实施前的设计方案 | 实施前撰写，实施后归档 |
| **Manual** | `docs/manual/` | 面向开发者的活文档 | **代码变更后同步更新** |

### Survey

Survey 为 plan 提供设计依据，不直接指导编码。命名格式：`docs/survey/YYYY-MM-DD_<topic>.md`。

示例：`docs/survey/2026-05-24_crypto_exchange_mechanisms_survey.md` §13.2 的优先级排序被 P1+P2 plan 引用。

### Plan

Plan 必须包含：目标与范围、架构变更、详细设计、测试策略、实现状态（checklist）。命名格式：`docs/plan/YYYY-MM-DD_<brief_description>.md`。

若依赖其他 plan 或 survey，在文档开头明确引用。

### Manual

Manual 是**面向开发者的活文档**，存放于 `docs/manual/` 下，反映代码库的**最新现状**。

**核心原则**：

1. **面向开发者**：Manual 不是用户手册，是帮助开发者理解系统、快速上手的内部文档。内容应聚焦架构决策、扩展指南、接口约定等开发者关心的问题。
2. **反映最新代码库现状**：Manual 必须与代码保持同步。若发现文档与代码不符，以代码为准并修正文档。
3. **完成代码变更后记得检查和更新**：任何涉及架构、接口、行为变更的代码修改完成后，都应检查相关 Manual 是否需要同步更新。

并鼓励在代码中编写注释和文档字符串。
