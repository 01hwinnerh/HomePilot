# HomePilot 项目总计划

**目标：** 构建用于 AI 应用 / Agent 开发岗位作品集展示的多商家精品家居平台，突出 FastAPI 交易能力、RAG、LangGraph、LangSmith、可审计 Agent 与多租户安全。

## 当前状态

- 当前阶段：阶段 1 — 身份、租户、商家与商品
- 当前状态：`in_progress`
- 项目名称：HomePilot
- 最近确认：用户已通过 uv 安装 Python 3.12；所有安装与 Git 命令由用户手动执行。
- 最近确认：采用“稳定大版本 + 锁文件固定精确版本”的依赖策略。
- 当前模块：身份、租户与认证实施计划（已确认，待创建文档 PR）。
- 当前阻塞：无。

## 阶段追踪

| 阶段 | 目标 | 状态 | 验收结果 |
|---|---|---|---|
| 0 | 环境基线、依赖锁定、工程骨架与本地基础设施 | 已完成 | PR #1 已合并，全量回归通过 |
| 1 | 身份、租户隔离、商家、店铺、商品与库存 | 进行中 | 数据库基础层 PR 已合并；身份认证设计已确认 |
| 2 | 跨店购物车、订单、库存预占与模拟支付 | 未开始 | — |
| 3 | 售后策略版本、规则引擎、售后状态机 | 未开始 | — |
| 4 | 知识版本、异步索引、RAG 与跨店对比 | 未开始 | — |
| 5 | LangGraph Agent、持久化、确认动作、人工接管 | 未开始 | — |
| 6 | 前端体验、观测、LangSmith 评测、部署与作品集文档 | 未开始 | — |

## 当前阶段任务

- [x] 确认项目名为 `HomePilot`。
- [x] 确认 uv 管理的 Python 3.12 已由用户安装。
- [x] 创建可持续维护的计划、发现与进度文档。
- [x] 确认 Python、前端、Docker、Agent/RAG 依赖版本矩阵策略。
- [x] 由用户手动创建项目虚拟环境并安装后端锁定依赖。
- [x] 由用户手动安装前端锁定依赖。
- [x] 创建后端、前端、基础设施与测试骨架。
- [x] 由用户手动启动 Docker Compose 并验证服务健康。
- [x] 锁定 Qdrant/MinIO 已验证镜像 digest。
- [x] 运行工程骨架小型全量回归。
- [x] 完成 `chore/project-scaffold` Commit 与 GitHub PR #1。
- [x] 完成数据库基础层 Commit 与 GitHub PR，已合并至 `main`。
- [x] 确认身份、refresh token、CSRF、RBAC 与多租户隔离设计；规格见 `docs/superpowers/specs/2026-08-05-identity-tenancy-auth-design.md`。
- [x] 编写身份、租户与认证的 TDD 实施计划；见 `docs/superpowers/plans/2026-08-05-identity-tenancy-auth-implementation.md`。

## 当前模块：数据库基础层

- [x] Red：为数据库 Settings、SQLAlchemy Database 封装和 Base metadata 写失败单元测试，已确认因目标模块缺失而失败。
- [x] Green：实现集中数据库配置、AsyncEngine/Session 和命名约定，4 个单元测试连续两次通过。
- [x] Quality：Ruff import 格式问题已修复，用户复验全量静态检查通过。
- [x] Alembic：创建可运行的异步迁移基线。
- [x] Integration：验证 MySQL 连通、事务回滚和 Alembic upgrade。
- [x] Regression：审查修复后后端 11 个测试、Ruff 及工程小型全量回归通过，复审无 Critical/Important。
- [x] 完成 `feat/database-foundation` Commit 与 GitHub PR。

## 更新约定

1. 每个阶段开始前更新本文件的“当前状态”和“当前阶段任务”。
2. 每完成一个可验证单元，记录到 `progress.md`；环境与兼容性结论记录到 `findings.md`。
3. 任何架构变更先更新 `docs/adr/` 与实施计划，再修改代码。
4. 任何依赖冲突、外部服务缺失或连续失败三次的事项都标注为阻塞，并先向用户说明。
5. 每个可独立说明的模块完成后，先提示用户手动执行 Commit 并发起 GitHub PR；下一模块不得与该 Commit 混合。Commit 信息采用 Conventional Commits，并准确描述本模块边界。
6. 预期必然失败的 TDD Red、诊断命令和静态探针由助手执行并记录；用户主要执行 Green、阶段回归、安装/Docker 状态变更和 Git 命令，且每条用户命令都说明目录、作用与预期结果。

## 非范围

首版不接入真实支付、物流、商家结算、发票、税务、扫描件 OCR；不使用 Saga 或 Redis-first 库存真源。
