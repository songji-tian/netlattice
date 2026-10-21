<!-- purpose: NetLattice 对外入口：一句话交给 AI，按 AGENTS.md 部署 DNS / VPN / Compute -->

# NetLattice

**把这个仓库交给你的 AI 编程工具（Claude Code、Codex 等），它会在你自己的机器上部署并验证一套内网基础设施。**

对 AI 说这一句就够了：

> 请阅读 https://github.com/songji-tian/netlattice 里的 AGENTS.md，按它帮我部署。需要哪些信息就问我。

## 你会得到

- **DNS**：AdGuard Home 提供内网域名解析、上游分流、过滤和查询日志。
- **VPN**：WireGuard 提供公网入口，把远程设备接回内网；可选 wg-easy 管理界面。
- **Compute**：Proxmox VE 模板、完整克隆、cloud-init、开机/关机/删除和基础监控。

三个模块可以只选一个，也可以组合。Agent 会读取同一份 `topology.yaml`，只部署你启用的模块。

## 选择模块

| 模块 | 解决什么 | 什么时候启用 | Agent 手册 |
|---|---|---|---|
| DNS | 内网域名、上游分流、过滤 | 家里或办公室需要 `pve.home.arpa` 这类内部名字 | [`modules/dns/AGENTS.md`](modules/dns/AGENTS.md) |
| VPN | 公网访问内网、远程开发 | 人不在内网，或需要把多地网络连起来 | [`modules/vpn/AGENTS.md`](modules/vpn/AGENTS.md) |
| Compute | 虚拟机模板、快速克隆、测试环境 | 有一台 Proxmox VE，想快速开干净机器 | [`modules/compute/AGENTS.md`](modules/compute/AGENTS.md) |

只做 DNS 和 VPN 的家庭网络很常见；只有一台 PVE、不需要内网 DNS 的场景也很常见。按需启用，不必全装。

## 先判断你属于哪种场景

这套项目最适合“自己有机器、自己管网络”的家庭或小办公室。先看网络入口，再看机器。

### A. 家里有公网 IP

- 光猫/路由器的 WAN 拿到公网 IPv4，不是 `100.64.0.0/10`，也不是 `10/8`、`172.16/12`、`192.168/16` 私网。
- 在路由器上把 `51820/udp` 转发到跑 VPN 的机器；动态 IP 配 DDNS，`WG_HOST` 填域名。
- 只有公网 IPv6 时需额外确认：Docker 要能把 `51820/udp` 发布到 IPv6，防火墙放行，客户端网络也要有 IPv6，DDNS 用 AAAA；默认只保证 IPv4，很多酒店/公司网络也没有 IPv6。
- 适合：远程回家、访问 NAS/PVE、给家里云做入口。

### B. 光猫桥接，路由器或服务器拨号

- **路由器拨号**：公网 IP 在路由器上，按场景 A 做端口映射。
- **服务器拨号**：服务器直接拿公网 IP，但同时要承担 LAN 网关、NAT、DHCP；单网卡服务器拨号会切断 LAN 原有上网，没有双网卡或网络经验时不要选。
- **光猫仍路由、下面再接路由器**：会出现双重 NAT。优先改桥接；改不了就在两层都做转发或 DMZ。
- **WAN 是 CGNAT**（`100.64/10` 或私网）：直接入站 WireGuard 不通。先看有没有公网 IPv6 可走；没有就需要公网中继/VPS，不能靠端口映射解决。

### C. 一台闲置机器做家里云

- **只跑 DNS + VPN**：Linux + Docker，`1–2 vCPU / 1–2 GB 内存 / 8–16 GB 磁盘`起步；AdGuard 查询日志别留太久。
- **还要跑 Compute**：机器需要先装 Proxmox VE；DNS/VPN 建议放在 PVE 里的一台小 VM/LXC，Compute 管理同一台 PVE 上的其他 VM。
- **只有一台普通 Linux、没有 PVE**：只启用 DNS/VPN，Compute 留空。

## 部署前准备

1. **网络**：确认公网 IP 还是 CGNAT、是否需要 DDNS、路由器能否做 `51820/udp` 端口映射；准备 LAN CIDR、DNS 地址、VPN CIDR。
2. **一台能 SSH 登录的 Linux 主机**（DNS/VPN 模块需要 Docker 和 Compose）。
3. **一台 Proxmox VE**（仅 Compute 模块需要），以及一个权限受限的 API token。
4. **一份拓扑文件**：复制 [`topology.example.yaml`](topology.example.yaml) 为 `topology.yaml`，按你的网络填写。
5. **缺失的密钥**：AdGuard 管理员密码、wg-easy 管理员密码哈希、PVE API token。Agent 会在需要时向你索取。
6. **一个能执行命令、编辑文件的 AI 编程工具**。
7. **先做三个决定**：启用哪些模块；VPN 是分流还是全局；管理界面只绑 `127.0.0.1` 还是 LAN。

Agent 会自己跑预检、校验、部署和验证。你只需要提供它拿不到的信息，以及确认危险操作。

## Agent 会怎么做

1. 读 `AGENTS.md` 和 `topology.yaml`。
2. 确认启用了哪些模块，只询问缺失的密钥和访问方式。
3. 预检端口、Docker、PVE API、磁盘和网络，不修改任何东西。
4. 校验拓扑，给出将要创建/修改/删除的清单。
5. 按 `dns → vpn → compute` 顺序部署。
6. 逐项验证，交一份真实结果报告；失败就停下来修，不假装成功。

## 部署完成后

Agent 应该给你：

- 每个模块的 `PASS / FAIL / SKIPPED` 报告，以及实际执行的命令和输出。
- DNS、VPN、PVE 的访问地址，和每个地址只允许从哪些网络访问。
- 一条明确的回滚路径：配置目录、容器名、数据目录、恢复命令。
- 需要你人工确认的项，尤其是外部网络才能验证的项，必须标成 `USER-VERIFY`，不能写成 PASS。

你还需要自己做：

1. **从手机蜂窝网络测试 WireGuard**（关闭 Wi-Fi）。家里 Wi-Fi 能连，不代表公网入口可用。
2. 把路由器 DHCP 下发的 DNS 改成 AdGuard 地址；否则只有手动配置 DNS 的设备会用到内网域名。
3. 确认 DDNS 指向当前公网地址，路由器只开放 `51820/udp`，管理界面没有暴露到公网。
4. 把 `topology.yaml`、各模块 `.env`、AdGuard 配置、WireGuard 数据目录备份到加密位置；不要提交 Git。
5. 记录当前镜像版本和 PVE 模板版本，升级前先看 changelog，再滚动重启。

## 安全边界

- 管理界面默认只绑定 `127.0.0.1` 或内网地址，不直接暴露公网。
- 公网只放 WireGuard 的 `51820/udp`；PVE 的 `8006` 不应对公网开放。
- 密钥只从环境变量、文件或密钥管理器读取，不写入 `topology.yaml`、日志或 Git。
- 删除虚拟机、撤销 peer、覆盖配置等危险操作，Agent 必须先确认。
- 仓库里的示例只使用 `home.arpa`、`example.com` 和文档网段，不含真实环境信息。

## 这不是什么

- 不是一键安装 Proxmox VE 的脚本；Compute 模块假设 PVE 已经运行。
- 不是公网 DNS 托管、TLS 证书签发或域名注册服务。
- 不是把现有生产环境自动迁移过来的工具；它只管理 `topology.yaml` 里声明的资源。

## 许可

Apache-2.0。见 [`LICENSE`](LICENSE)。
