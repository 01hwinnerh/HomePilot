# HomePilot 交接入口

**任何新的 Coding Agent 或恢复开发的对话，都必须先阅读本文件。**

详细交接内容在：[docs/handover/2026-08-06-homepilot-handoff.md](docs/handover/2026-08-06-homepilot-handoff.md)。

## 当前快照

- 项目：HomePilot，多商家精品家居平台 + 可审计 RAG/Agent 客服。
- 已合并：工程骨架、Docker 基础设施、数据库/Alembic、身份数据模型、认证 API、租户硬隔离。
- 上一次后端回归：`65 passed`，Ruff 通过；既有 Starlette `TestClient` 弃用警告暂不处理。
- Storefront 顾客认证 UI PR 已合并；本地是否已切回并同步 `main` 由用户自行确认，不要自行执行 Git 命令。
- `@homepilot/auth-client` 已独立合并。
- Storefront 顾客认证闭环已合并，覆盖登录、注册、启动恢复和退出；相关测试、计划与交接记录已同步。
- Console 登录、商家/平台身份展示 PR 已合并；本地 `main` 已同步且工作区干净。
- 当前模块：GitHub Actions CI 方案 A 的首次 PR 发现前端 pnpm 配置错误和后端 MySQL 初始化失败；前端已修复，后端已增加初始化防护与失败日志，等待用户推送修复并重新观察 CI。
- 下一模块：身份演示种子数据与前后端联调；必须在 CI PR 合并并更新交接文档后再开始。

## 恢复开发的固定顺序

1. 阅读根目录 `AGENTS.md`、`task_plan.md`、`findings.md`、`progress.md`。
2. 阅读详细交接文档与身份实施计划：
   `docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`。
3. 保持中文沟通；用户自己执行 Git、安装和 Docker 状态变更命令。
4. 每一个小模块必须执行“四步学习协议”：概念课（用户明确“真的听懂了”后编码）→ 纵向 TDD 开发 → 按数据流代码讲解 → 生成 5 题复述材料与参考答案。
5. Agent 内部执行 Red/定向测试；复述材料生成后即可给出独立 Commit、push 和 PR 内容，用户可自行复述学习但不阻塞流程。

## 不可违反的安全约束

- 不读取、输出或修改 `.env` 中的真实密钥。
- access JWT 只表示用户 ID；商家权限必须从数据库实时构造。
- access token 只允许内存保存；禁止 `localStorage`、`sessionStorage`、URL 或 Zustand persist。
- MySQL 是交易真源；Redis 不是库存真源。
- 新依赖、版本冲突或 Docker 兼容问题：先写入 `findings.md`，说明方案并等待用户确认。

## 已知注意事项

- 后端真实字段是 `user.memberships`，不是旧草案中的 `merchant_memberships`。
- 新 workspace 包首次运行测试需要用户在 `frontend` 执行普通 `pnpm install`；`--lockfile-only` 不会建立可执行依赖链接。

