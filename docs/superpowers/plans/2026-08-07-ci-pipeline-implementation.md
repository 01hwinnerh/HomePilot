# GitHub Actions CI 流水线实施计划

> 本计划对应方案 A：一个 `ci.yml`，包含 Backend 和 Frontend 两个独立 Job。CI 只做持续集成检查，不执行部署。

## 目标

为 HomePilot 建立可审计的 GitHub Actions PR 门禁：任何提交到 `main` 的 Pull Request 都必须通过后端和前端质量检查，合并后在 `main` 再留下最终验证记录。

## 已确认边界

- 不调用真实 DeepSeek、LangSmith、SiliconFlow 或 MinIO 密钥。
- 不在第一版 CI 中执行生产部署。
- 不把外部模型延迟作为 PR 合并硬门槛。
- Backend 集成测试需要 MySQL/Redis；CI 使用临时服务和仅供测试的环境变量。
- Frontend 使用 `pnpm-lock.yaml` 的 frozen install，禁止 CI 自动改锁文件。
- Frontend workspace 的测试脚本必须保持一次性执行模式（当前为 `vitest run`），不得改成 watch mode。
- workflow 使用最小权限 `contents: read`，并取消同一 PR 的过时运行。

## Workflow 结构

文件：`.github/workflows/ci.yml`

### 触发与并发

- `pull_request`：目标分支为 `main`。
- `push`：仅 `main`，用于合并后的最终记录。
- `workflow_dispatch`：允许维护者手动重跑。
- `concurrency`：同一 PR/分支只保留最新运行，节省分钟数。
- 两个 Job 都设置 `timeout-minutes: 15`；MySQL/Redis 启动另设 120 秒 Compose 健康等待上限。

### Job 1：backend

运行环境：`ubuntu-latest`、Python 3.12、锁定版本 uv。

步骤顺序：

1. checkout 代码。
2. 安装 uv，并启用 uv 缓存。
3. `uv sync --locked --all-groups`，验证 `uv.lock` 没有漂移。
4. 启动 MySQL 8.4 与 Redis 7.4，使用 Compose `--wait` 等待既有 healthcheck；MySQL 初始化脚本创建隔离的 `homepilot_test`。
5. 注入 `AUTH_JWT_SECRET=ci-only-test-secret` 等非敏感测试变量；不读取 GitHub Secrets。
6. 执行 `uv run pytest -q`。
7. 执行 `uv run ruff check .`。

### Job 2：frontend

运行环境：Node 24.14.1、pnpm 11.9.0。

步骤顺序：

1. checkout 代码。
2. 使用 pnpm/action-setup 配置 pnpm 11.9.0。
3. 使用 setup-node 配置 Node 24 并启用 pnpm store 缓存。
4. `pnpm install --frozen-lockfile`。
5. `pnpm run test`。
6. `pnpm run build`。
7. `pnpm run lint`。

## 分阶段实现

### Task 1：创建 workflow 骨架

- [x] 只写触发器、权限、并发和两个 Job 的名称。
- 先进行 YAML 静态审阅，不立即添加复杂缓存或外部服务。

### Task 2：接入 Backend 检查

- [x] 增加 Python/uv 安装、MySQL/Redis 服务、CI 环境变量和后端测试命令。
- [x] 确认测试数据库名称包含 `test` 且不同于业务库。

### Task 3：接入 Frontend 检查

- [x] 增加 Node/pnpm 安装、frozen lockfile、测试/构建/lint。
- [x] 确认 `esbuild` 只执行既有白名单脚本，不放开其他依赖脚本。

### Task 4：本地审阅与 PR 验证

- [x] 审阅 Actions 权限、密钥边界、缓存 key、Job 依赖和失败行为。
- [x] 用户在 GitHub Actions 页面观察两个 Job 的日志；首次 Runner 发现并修复 pnpm 构建批准、workspace ESLint、MySQL entrypoint shell 选项和 health 测试环境断言问题。
- [x] 修复后 `backend` 与 `frontend` 两个 Job 均通过，CI PR 已合并。

### Task 5：启用 main 分支保护

- 在 GitHub Settings → Branches/Rules 中要求 Pull Request。
- 将 `backend`、`frontend` 两个 CI check 设置为 required。
- 禁止直接 push 到 `main`，保留管理员紧急例外并记录原因。

## 验收标准

- PR 自动触发 CI，Backend 和 Frontend 两个 Job 均通过。
- 锁文件漂移、后端测试失败、前端测试/build/lint 失败时，PR 不允许合并。
- CI 日志不出现真实 API Key、JWT secret、数据库生产密码或 Cookie 内容。
- 合并到 `main` 后自动产生一次 push 检查记录。
- CI 失败时可以通过 Job 日志定位到具体命令，而不是只显示笼统失败。

## 后续扩展

- 独立 Docker integration Job：Qdrant/MinIO/完整 Compose 健康检查。
- nightly LangSmith 评测：使用 GitHub Encrypted Secrets 和成本上限。
- 预发布部署 workflow：必须在生产前置检查完成后另行设计，不与本 CI 混合。
