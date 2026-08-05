# HomePilot 实施计划

> **面向执行者：** 按阶段和验收点递增实现。每完成一个可验证单元，更新根目录的 `task_plan.md`、`findings.md`、`progress.md`；发生架构变更时先补充 ADR。

**目标：** 构建展示多商家交易能力、RAG、LangGraph Agent、安全控制与可观测性的家居电商作品集。

**架构：** 前端 monorepo 包含用户商城和商家/平台控制台；后端是 FastAPI 模块化单体，以 MySQL 作为交易和审计真源，Redis 承担异步和活跃 checkpoint，Qdrant 与 MinIO 承担版本化知识检索。Agent 只通过服务端注入的身份上下文调用领域工具。

**技术栈：** Python 3.12 + uv、FastAPI、SQLAlchemy、Alembic、MySQL 8.4、Redis 7.4、Celery、React、TypeScript、Vite、LangChain、LangGraph、LangSmith、Qdrant、MinIO、Docker Compose。

**版本策略：** 使用稳定大版本范围，首次安装后由 `uv.lock`、`pnpm-lock.yaml` 固定精确版本；Docker 的 Qdrant 与 MinIO 在首次成功拉取后记录精确 tag/digest。依赖解析或框架兼容问题必须先向用户说明，不能自行替换。

**Git 协作：** 每个可独立说明的模块完成后，先提示用户手动提交一个准确的 Conventional Commit，并创建或更新 GitHub PR；后续模块不得混入该 Commit。

---

## 阶段 0：环境基线与工程骨架

- [x] 确认项目展示名称：HomePilot。
- [x] 用户安装 uv 管理的 Python 3.12。
- [x] 确认依赖版本策略：稳定大版本 + 锁文件。
- [x] 生成 `pyproject.toml`、`package.json` 与 Compose 镜像标签，并由用户完成首次安装/拉取。
- [x] 创建 `.env.example`、Docker Compose、后端与前端 workspace、测试及代码质量配置。
- [x] 由用户启动基础设施并完成后端健康检查、前端空页面、测试基线验证。

**验收：** 新开发者可依据 README 和 `.env.example` 连接本地服务，两个前端应用、后端健康检查和空测试集均可运行。

## 阶段 1：身份、租户、商家与商品

- [ ] 建立用户认证、RBAC、`TenantContext` 与平台/商家角色。
- [ ] 对商家归属数据实施显式 tenant/principal Repository 参数和 SQLAlchemy 额外过滤。
- [ ] 建立商家、店铺、成员、商品、SKU、库存、图片和上下架模型与接口。
- [ ] 完成商城商品浏览和控制台商品管理的最小闭环。

**验收：** 商家 A 无法读取或修改商家 B 的资源；平台角色只经独立 Repository 执行跨租户查询。

## 阶段 2：跨店交易与模拟支付

- [ ] 建立购物车、平台主订单、商家子订单、订单项、库存预占和幂等记录。
- [ ] 在单个 MySQL 事务内固定 SKU ID 顺序、条件更新库存并创建 15 分钟预占。
- [ ] 实现支付确认、重复回调幂等和定时过期释放。
- [ ] 通过 Transactional Outbox 处理事务后通知与统计。

**验收：** 任一 SKU 缺货时全部回滚；并发结算不超卖；重复回调不重复扣减。

## 阶段 3：售后策略与闭环

- [ ] 实现不可变 `PolicyVersion`、内容哈希、订单项版本引用和售后结构化条款。
- [ ] 实现平台最低保障、商家更优条款与强制规则优先的策略裁决和决策轨迹。
- [ ] 实现预检、用户确认、商家审核、模拟签收、模拟退款、平台复核状态机。

**验收：** 历史订单遵循历史策略；退款金额不超过可退实付金额；高风险动作有审计和人工复核入口。

## 阶段 4：版本化知识库与 RAG

- [ ] 支持 Markdown、DOCX 和含文本层 PDF，明确拒绝扫描件。
- [ ] 实现 MinIO 不可变文档版本、审核、Celery 索引、Qdrant 元数据和安全切换。
- [ ] 实现单商品范围检索、跨店公开商品白名单比较、分店引用与静态 FAQ 降级。

**验收：** 新旧版本不会混合召回；禁用商家/商品即时撤销检索权限；跨店回答不混淆商家承诺。

## 阶段 5：可信 Agent 与人工接管

- [ ] 实现 DeepSeek Provider Factory、Fake Chat Model、集中配置和 LangGraph 状态图。
- [ ] 实现权限预检、意图路由、RAG、查单、售后预检、草稿与确认动作。
- [ ] 使用 RedisSaver 管理 24 小时 checkpoint，MySQL 保存会话、摘要、动作、工单和审计真源。
- [ ] 实现 SSE、断线恢复、工具二次鉴权、自动创建工单和人工接管停答。

**验收：** 模型不能伪造身份或跳过确认；人工接管获得完整消息、证据与待处理动作。

## 阶段 6：体验、观测、评测与作品集

- [ ] 完成用户商城和商家/平台控制台的交易、售后、知识审核和工单体验。
- [ ] 接入结构化日志、Sentry、Prometheus/Grafana、LangSmith Trace。
- [ ] PR 运行单元、集成、前端检查和 12 条 Agent 冒烟评测；nightly 运行 60+ 条完整评测。
- [ ] 完成演示数据、架构图、部署指南、演示脚本和简历项目描述。

**验收：** 作品集可本地一键演示，评测结果可追踪，核心安全与交易场景均有自动化测试。
