# NetLattice · 网织

**Agent-first LAN/WAN fabric for DNS, WireGuard, and Proxmox.**

NetLattice 是一套面向家庭实验室、小型办公室和企业内网的**网络拓扑管理方案**。它把三件常被分开维护的事，收敛到一份 `topology.yaml`：

- **DNS**：AdGuard Home 提供内网域名解析、上游分流、过滤与审计。
- **VPN**：WireGuard 提供公网入口，把远程设备安全地接回内网。
- **Compute**：Proxmox VE 提供虚拟机/模板/克隆能力，快速构建纯净测试与开发环境。

它不是一个传统意义上的“安装脚本集合”。它的第一等公民是 **给 Agent 读的部署契约**：

> 看这个项目，并根据项目内容部署。

Agent 读完 [`AGENTS.md`](AGENTS.md)，按 `topology.yaml` 生成计划、执行部署、逐项验证。人只负责提供缺失的密钥和做危险操作确认。

## 为什么是 Agent-first

传统自托管项目的 README 假设读者是“有耐心的人”：读文档、改配置、逐条执行、遇到报错再搜索。

NetLattice 假设读者是 **Agent**，同时让人仍然能审计：

- `topology.yaml` 是唯一事实源，人和 Agent 看同一份意图。
- `AGENTS.md` 是部署契约，定义输入、顺序、幂等、验证、回滚和禁止事项。
- 每个模块有独立的 `AGENTS.md`，可以单独部署，也可以由总入口编排。
- 所有操作必须 `plan → apply → verify`，不允许“先跑了再说”。
- 密钥只从环境变量、文件或密钥管理器读取，**永不写入仓库、日志、计划文件**。

## 三模块

| 模块 | 解决什么 | 默认实现 | 管理界面 |
|---|---|---|---|
| [`modules/dns`](modules/dns/README.md) | 局域网 DNS 管理、内网域名、上游分流、过滤 | AdGuard Home | AdGuard Home 自带 |
| [`modules/vpn`](modules/vpn/README.md) | 公网访问内网、远程开发、站点互联 | WireGuard + wg-easy | wg-easy 自带 |
| [`modules/compute`](modules/compute/README.md) | 局域网机器虚拟化、模板、快速克隆 | Proxmox VE + API | `console/` 参考实现（只读） |

三个模块可以独立使用；放在同一个仓库里，是因为它们共享同一张拓扑和同一套安全边界。后续可以把任一模块拆成独立仓库，`topology.yaml` 和 `AGENTS.md` 契约不变。

## 架构

```text
                         ┌─────────────────────────────┐
                         │        topology.yaml        │
                         │  sites / networks / nodes   │
                         │  dns / vpn / compute        │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────▼──────────────┐
                         │          AGENTS.md          │
                         │  preflight → plan → apply   │
                         │  → verify → report          │
                         └──────────────┬──────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
┌─────────▼─────────┐         ┌─────────▼─────────┐         ┌─────────▼─────────┐
│   DNS module      │         │   VPN module      │         │  Compute module   │
│   AdGuard Home    │◄───────►│   WireGuard       │◄───────►│   Proxmox VE      │
│   :53 / :3000     │  split  │   :51820/udp      │  reach  │   :8006 API       │
└─────────┬─────────┘  DNS    └─────────┬─────────┘         └─────────┬─────────┘
          │                             │                             │
          └─────────────────────────────┴─────────────────────────────┘
                                        │
                              LAN / WAN / VPN overlay
```

## 快速开始（给 Agent）

```bash
git clone https://github.com/songji-tian/netlattice.git
cd netlattice
cp examples/home-lab.yaml topology.yaml
python3 scripts/validate_topology.py topology.yaml
```

然后把这句话交给 Agent：

> 读 `AGENTS.md`，按 `topology.yaml` 部署。缺的密钥问我，危险操作先确认。

或者直接给项目地址：

> 看 https://github.com/songji-tian/netlattice ，并根据项目内容部署。

## 仓库结构

```text
.
├── AGENTS.md                 # 总部署契约（Agent 入口）
├── PROMPT.md                 # 一句话部署提示词
├── README.md
├── SECURITY.md
├── CONTRIBUTING.md
├── LICENSE
├── topology.example.yaml
├── console/                  # v0.2 只读参考控制台
│   ├── app.py
│   ├── topology.py
│   ├── render.py
│   ├── static/index.html
│   ├── Dockerfile
│   └── compose.yaml
├── tests/                    # console 单元/API 测试
├── docs/
│   ├── architecture.md
│   ├── topology-schema.md
│   ├── security.md
│   └── api/
│       └── README.md         # 统一 API 契约
├── modules/
│   ├── dns/
│   ├── vpn/
│   └── compute/
├── examples/
│   ├── home-lab.yaml
│   └── small-office.yaml
├── scripts/
│   └── validate_topology.py
└── .github/workflows/
    └── validate.yml
```

## 参考 Console（v0.2）

`console/` 是一个**只读**参考控制台：读 `topology.yaml`，展示拓扑、DNS 记录、VPN peer、Compute 模板，并生成安全预览。它不连接 AdGuard、WireGuard 或 Proxmox，不会修改任何基础设施。

本地运行：

```bash
python3 -m venv .venv
.venv/bin/pip install -r console/requirements.txt
.venv/bin/uvicorn console.app:app --host 127.0.0.1 --port 8787
```

或容器运行：

```bash
docker compose -f console/compose.yaml up --build
```

打开 `http://127.0.0.1:8787`。默认读取 `topology.example.yaml`；切换拓扑：

```bash
NETLATTICE_TOPOLOGY=examples/home-lab.yaml \
  .venv/bin/uvicorn console.app:app --host 127.0.0.1 --port 8787
```

主要接口：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 服务与拓扑状态 |
| GET | `/api/site` | 站点/节点/网络/模块总览 |
| GET | `/api/dns` | DNS 记录与 AdGuard 预览 |
| GET | `/api/vpn` | peer 列表与 WireGuard 服务端预览 |
| GET | `/api/vpn/peers/{name}/config` | 单个 peer 客户端配置（私钥占位） |
| GET | `/api/compute` | 模板与克隆计划（只读） |
| GET | `/api/render` | 全部预览文件 |
| GET | `/openapi.json` | OpenAPI 3 文档 |

> 这是**契约参考实现**，不是 v0.3 的 apply 引擎。`render` 输出中的私钥字段是占位符，不能直接上线。

## 当前状态

- **v0.1**：Agent 契约、拓扑 schema、三模块边界、DNS/VPN 参考 compose、校验器、示例。
- **v0.2（当前）**：只读参考 Console、DNS/WireGuard/Compute 安全预览、OpenAPI、单元/API 测试与容器。
- **v0.3**：拓扑驱动的 apply 引擎：DNS 记录、WireGuard peer、PVE 克隆/开机；带 dry-run、幂等与回滚。
- **v1.0**：一键 Agent 部署、端到端验证、升级与回滚。

## 安全

NetLattice 默认假设管理面**不暴露在公网**：

- AdGuard 管理端口、PVE API、wg-easy 管理端口只绑定 LAN 或 VPN。
- 公网只放 WireGuard UDP 端口（以及必要的 HTTPS 入口）。
- 所有密钥通过 `.env.local`、Docker secrets、systemd credentials 或外部密钥管理器注入；仓库只保留 `.env.example`。
- 公开部署前请阅读 [`SECURITY.md`](SECURITY.md) 和 [`docs/security.md`](docs/security.md)。

## License

Apache-2.0。见 [`LICENSE`](LICENSE)。
