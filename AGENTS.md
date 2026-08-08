# Repository Guidelines

## Mandatory Resume Checklist

Before making any implementation decision, read `HANDOFF.md`. It is the root-level entry point for the current project state, user collaboration rules, and the detailed session handoff.

Before creating an independent module's PR, update `HANDOFF.md`, `docs/handover/`, and the related plan/progress files with the latest verified capability, tests, and next-step context, and include those updates in the same PR. Do not record volatile branch or PR merge state in these files; GitHub and Git history are the source of truth for that state. Also update them immediately when the user explicitly requests a handoff refresh. These files must describe the latest verified state, not the original implementation plan.

## Mandatory Learning Collaboration Protocol

Every independent module follows four gates. This applies to documentation, infrastructure, backend, frontend, RAG, and Agent work.

1. **概念课（编码前）**：先用中文说明模块解决的问题、核心概念（生活化类比和本项目代码语境）、推荐方案及 2～3 个未采用方案和原因。只有用户明确表示“真的听懂了”，才可开始编码。
2. **开发**：采用纵向 TDD。Agent 自行运行必然失败的 Red、定向测试和诊断；用户在关键行为边界参与，不重复执行已知会失败或无信息增益的命令。
3. **代码讲解（完成后）**：按数据流说明“输入/请求进来 → 经历哪些组件与决策 → 返回/落库什么”，重点讲安全边界、关键选择和易错点。
4. **复述验收材料**：每个模块都要生成 5 题（2 个“是什么”、2 个“为什么”、1 个“如果……会怎样”）及参考答案，并归档至被 `.gitignore` 排除的 `.learning/`，只供用户学习，不上传 GitHub。用户可自主复述，但复述不阻塞后续开发、Commit 或 PR。

## Project Structure & Module Organization

HomePilot is a modular monolith for multi-merchant home retail and an agent-assisted support service. The backend lives in `backend/`: application code is split among `app/api/`, `app/core/`, `app/shared/`, and `app/modules/`; tests are in `tests/unit/` and `tests/integration/`; database revisions are in `alembic/versions/`. The pnpm workspace in `frontend/` contains `apps/storefront/` (customer UI) and `apps/console/` (merchant console), with source under each app’s `src/`. Designs, implementation plans, and ADRs live in `docs/superpowers/` and `docs/adr/`. Local infrastructure is defined in `docker-compose.yml`.

## Build, Test, and Development Commands

Copy `.env.example` to the untracked root `.env`, then run `./scripts/bootstrap.ps1` to check `uv`, Node, pnpm, and Docker.

- `docker compose up -d` starts MySQL, Redis, Qdrant, and MinIO.
- From `backend/`, run `uv run alembic upgrade head`, `uv run pytest`, and `uv run ruff check .` for migrations, tests, and linting.
- From `frontend/`, use `pnpm dev:storefront` or `pnpm dev:console` to start an app. Run `pnpm run build`, `pnpm run test`, and `pnpm run lint` before review.
- From the repository root, `./scripts/verify_stack.ps1` verifies backend and frontend checks plus container connectivity.

## Coding Style & Naming Conventions

Use four-space indentation and Python 3.12 type annotations. Ruff enforces a 100-character line limit; use `snake_case` for Python modules, functions, and variables, and `PascalCase` for classes. Follow the existing ESLint rules for TypeScript/React: components use `PascalCase` and hooks start with `use`. Keep HTTP concerns in `api/`, domain behavior in the relevant `modules/` package, and reusable database or tenancy code in `shared/`.

## Testing and Migrations

The backend uses pytest/pytest-asyncio and the frontend uses Vitest. Name tests `test_*.py` or `*.test.ts`; cover both the expected path and important rejections. Integration tests must use `TEST_DATABASE_URL`: its database name must contain `test` and differ from the business database. Never edit a merged Alembic migration. Create a new revision with `uv run alembic revision --autogenerate -m "describe schema change"`.

## Commits, Pull Requests, and Security

History follows Conventional Commits, for example `feat(auth): add rotating session authentication API` and `docs: define identity and tenancy implementation`. Use concise `type(scope): summary` messages and keep each commit focused. PRs should state the purpose, checks run, and any migration or configuration impact; link issues and include screenshots for UI changes. Never commit `.env`, JWT secrets, database passwords, or provider API keys. Production requires secure cookies and an explicit CORS allowlist.
