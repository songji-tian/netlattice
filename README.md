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

## 你需要准备

1. **一台能 SSH 登录的 Linux 主机**（DNS/VPN 模块需要 Docker 和 Compose）。
2. **一台 Proxmox VE**（仅 Compute 模块需要），以及一个权限受限的 API token。
3. **一份拓扑文件**：复制 [`topology.example.yaml`](topology.example.yaml) 为 `topology.yaml`，按你的网络填写。
4. **一个公网入口**（仅 VPN 需要）：公网 IP 或域名，以及可用的 `51820/udp`。
5. **缺失的密钥**：AdGuard 管理员密码、wg-easy 管理员密码哈希、PVE API token。Agent 会在需要时向你索取。
6. **一个能执行命令、编辑文件的 AI 编程工具**。

Agent 会自己跑预检、校验、部署和验证。你只需要提供它拿不到的信息，以及确认危险操作。

## Agent 会怎么做

1. 读 `AGENTS.md` 和 `topology.yaml`。
2. 确认启用了哪些模块，只询问缺失的密钥和访问方式。
3. 预检端口、Docker、PVE API、磁盘和网络，不修改任何东西。
4. 校验拓扑，给出将要创建/修改/删除的清单。
5. 按 `dns → vpn → compute` 顺序部署。
6. 逐项验证，交一份真实结果报告；失败就停下来修，不假装成功。

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
