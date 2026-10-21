<!-- purpose: Reference HTTP API for the compute module; sanitized from the private MVP. -->
# Compute module HTTP API (reference)

> **Status:** reference contract. The optional read-only console implements a subset; verify the endpoint you need against the implementation you are running.

# netlattice-console · HTTP API

> 面向开发者、脚本和 Agent 的接口手册。
>
> - 镜像：`netlattice-console:dev`
> - 局域网域名：`https://console.example.com`
> - 直连回退：`http://192.168.10.2:8787`（仅内网，建议优先 HTTPS）
> - OpenAPI：`GET /openapi.json`（Swagger UI 未开启）
> - 共 13 个 API 操作（12 个唯一路径），全部返回 JSON；另有 `GET /` 返回静态页面

---

## 0. 快速开始

```bash
BASE=https://console.example.com
COOKIE=/tmp/pve-console.cookie

# 1) 登录，保存 HttpOnly Cookie
curl -sS -c "$COOKIE" \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"<管理员密码>"}' \
  "$BASE/api/login"

# 2) 查看虚拟机
curl -sS -b "$COOKIE" "$BASE/api/vms"

# 3) 查看某台机器详情
curl -sS -b "$COOKIE" "$BASE/api/vms/100"
```

> 本文档不包含真实管理员密码、虚拟机密码或 SSH 私钥。示例中的 `<...>` 需要由调用方从安全的凭据存储中获取。

---

## 1. 通用约定

### 1.1 认证

- 除 `GET /api/health` 和 `POST /api/logout` 外，所有业务接口都需要登录态。
- 登录成功后服务端设置 Cookie：

  ```http
  Set-Cookie: sid=<signed-token>; HttpOnly; SameSite=Lax; Max-Age=43200; Path=/
  ```

- 会话有效期 **12 小时**（`SESSION_TTL = 12 * 3600`）。
- 当前没有 Bearer Token / API Key 认证，也没有 refresh token；过期后重新调用 `/api/login`。
- 未登录或 Cookie 失效：`401 {"detail":"未登录"}`。
- 用户名或密码错误：`401 {"detail":"用户名或密码错误"}`。
- Cookie 当前未设置 `Secure` 标志，生产环境请始终通过 HTTPS 域名访问，避免明文 HTTP 直连泄露会话。

### 1.2 请求格式

- 请求体：`Content-Type: application/json`。
- 删除接口也使用 JSON 请求体（`DELETE` + body），不是 query 参数。
- 字段命名：`snake_case`。
- 时间：Unix 秒级时间戳（`ts` 为整数；日志 `ts` 为浮点数）。
- 字节：`mem`、`maxmem`、`disk`、`maxdisk`、`netin`、`netout`、`diskread`、`diskwrite` 单位均为 **bytes**。
- 百分比：`cpu`、`mem_pct` 为数值，前端直接显示；`mem_pct` 可能为 `null`。

### 1.3 响应与错误

成功响应一般为：

```json
{"ok": true}
```

业务错误使用 FastAPI 标准结构：

```json
{"detail": "错误说明"}
```

Pydantic 参数校验失败返回 `422`，结构为：

```json
{"detail": [{"loc": ["body", "name"], "msg": "String should have at least 1 character", "type": "string_too_short"}]}
```

| HTTP | 含义 | 典型场景 |
|---|---|---|
| `200` | 成功 | 查询、操作已提交 |
| `400` | 业务参数错误 | 名称不合法、模板不可删、没有可修改字段 |
| `401` | 未认证 | Cookie 缺失/过期、密码错误 |
| `404` | 资源不存在 | VMID、模板不存在 |
| `409` | 当前状态不允许 | VM 未启动、guest agent 未就绪 |
| `422` | 请求体校验失败 | 字段类型错误、超出范围、非法枚举 |
| `502` | 上游 PVE 失败 | PVE 连接失败、克隆/电源/删除任务失败 |

`GET /api/health` 失败时是例外：

```json
{"ok": false, "error": "..."}
```

HTTP 状态码为 `502`。

---

## 2. 端点总览

| 方法 | 路径 | 认证 | 用途 |
|---|---|---|---|
| GET | `/api/health` | 否 | 探活 + PVE 版本 |
| POST | `/api/login` | 否 | 登录，设置 `sid` Cookie |
| POST | `/api/logout` | 否 | 清除 `sid` Cookie |
| GET | `/api/vms` | 是 | 虚拟机列表（含实时指标/IP/创建中占位） |
| GET | `/api/vms/{vmid}` | 是 | 单机详情（配置/指标/连接方式/凭据） |
| POST | `/api/vms/{vmid}/action` | 是 | 开机/优雅关机/强制停止/重启 |
| POST | `/api/clone` | 是 | 从模板创建虚拟机（阻塞，直到克隆并开机） |
| DELETE | `/api/vms/{vmid}` | 是 | 删除虚拟机（需名称确认） |
| POST | `/api/vms/{vmid}/credentials` | 是 | 修改 Linux/Windows 凭据 |
| GET | `/api/defaults` | 是 | 新建虚拟机的服务端默认凭据 |
| GET | `/api/templates` | 是 | 可用模板列表 |
| GET | `/api/overview` | 是 | 节点、存储、数量概览 |
| GET | `/api/logs` | 是 | 操作审计日志 |

---

## 3. 认证接口

### 3.1 登录

`POST /api/login`

请求：

```json
{
  "username": "admin",
  "password": "<管理员密码>"
}
```

成功响应：

```json
{"ok": true, "user": "admin"}
```

同时设置 `sid` Cookie（HttpOnly、SameSite=Lax、12 小时）。

错误：

```json
{"detail": "用户名或密码错误"}
```

状态码 `401`。

### 3.2 退出

`POST /api/logout`

无需登录态；服务端删除 `sid` Cookie。

```json
{"ok": true}
```

---

## 4. 探活

### `GET /api/health`

无需登录。

成功：

```json
{
  "ok": true,
  "pve": {
    "version": "9.1.1",
    "release": "9.1",
    "repoid": "..."
  }
}
```

PVE 不可达时：

```json
{"ok": false, "error": "..."}
```

状态码 `502`。

---

## 5. 虚拟机接口

### 5.1 列表

`GET /api/vms`

响应：

```json
{
  "vms": [
    {
      "vmid": 100,
      "name": "win10-tian",
      "status": "running",
      "template": false,
      "node": "pve-1",
      "cores": 4,
      "cpu": 24.1,
      "mem": 3291021312,
      "maxmem": 8589934592,
      "mem_pct": 38.4,
      "mem_source": "guest",
      "disk": 0,
      "maxdisk": 107374182400,
      "uptime": 123456,
      "netin": 1500000000,
      "netout": 20000000,
      "diskread": 13000000000,
      "diskwrite": 29300000000,
      "ip": "192.168.10.50",
      "label": null,
      "history": [[1760000000, 24.1, 38.4]]
    }
  ],
  "ts": 1760000000
}
```

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `vmid` | int | PVE VMID |
| `name` | string | 虚拟机名 |
| `status` | string | `running` / `stopped` / `creating` |
| `template` | bool | 是否模板 |
| `node` | string | PVE 节点名 |
| `cores` | int \| null | vCPU 数 |
| `cpu` | number | CPU 使用率（百分比数值） |
| `mem` | int | 已用内存（bytes）；Windows 为 guest 真实已用 |
| `maxmem` | int | PVE 配置的内存上限（bytes） |
| `mem_pct` | number \| null | 内存百分比；Windows QGA 不可用时为 `null` |
| `mem_source` | string | `guest` / `host` / `guest-unavailable` |
| `disk` | int | 已用磁盘（bytes） |
| `maxdisk` | int | 磁盘上限（bytes） |
| `uptime` | int | 运行时长（秒） |
| `netin` / `netout` | int | 累计网络流量（bytes） |
| `diskread` / `diskwrite` | int | 累计磁盘 I/O（bytes） |
| `ip` | string \| null | guest agent 或 `ipconfig0` 解析出的 IP |
| `label` | string \| null | 模板显示名；普通 VM 为 `null` |
| `history` | array | 最近最多 60 个采样，元素为 `[ts, cpu_pct, mem_pct]` |
| `creating` | bool | 创建中的行出现：可能是进程内占位行，也可能是 PVE 已列出但克隆流程尚未结束的 VM |

“创建中”行为：

- 克隆请求尚未完成时，`/api/vms` 可能返回 `status="creating"` 的占位行。
- 如果 PVE 已经列出新 VM，列表行也会被覆盖为 `status="creating"`、`creating=true`、`ip=""`，CPU/内存显示为 0。
- 进程内占位状态最多保留 15 分钟；克隆接口返回后占位立即移除。

内存口径（重要）：

- **Linux**：优先 virtio-balloon；拿不到时回退宿主 RSS，`mem_source="host"`。
- **Windows**：通过 QGA 执行 WMI 查询 `Win32_OperatingSystem`，读取 `FreePhysicalMemory` / `TotalVisibleMemorySize`，换算成 bytes。
  - `mem_source="guest"` 表示真实客户机数据。
  - 15 秒缓存；QGA 超时 6 秒；失败重试节流 10 秒。
  - QGA 不可用：`mem=0`、`mem_pct=null`、`mem_source="guest-unavailable"`，前端显示“—”。
  - `mem_pct` 的分母是 Windows **可见内存总量**；`maxmem` 仍是 PVE 配置值，二者可能有少量差异。
- 首次查询 Windows 内存时，`/api/vms` 最坏可能多等待约 6 秒；Agent 调用建议设置 15 秒以上超时。

### 5.2 详情

`GET /api/vms/{vmid}`

成功响应：

```json
{
  "vmid": 100,
  "name": "win10-tian",
  "status": "running",
  "template": false,
  "node": "pve-1",
  "uptime": 123456,
  "ip": "192.168.10.50",
  "ostype": "win10",
  "is_windows": true,
  "macs": [
    {"if": "net0", "mac": "BC:24:11:AA:BB:CC", "raw": "virtio=BC:24:11:AA:BB:CC,bridge=vmbr0"}
  ],
  "agent": {},
  "metrics": {
    "cpu": 24.1,
    "cores": 4,
    "mem": 3291021312,
    "maxmem": 8589934592,
    "mem_pct": 38.4,
    "mem_source": "guest",
    "disk": 0,
    "maxdisk": 107374182400,
    "netin": 1500000000,
    "netout": 20000000,
    "diskread": 13000000000,
    "diskwrite": 29300000000,
    "uptime": 123456
  },
  "config": {
    "cores": 4,
    "sockets": 1,
    "memory": "8192",
    "ostype": "win10",
    "machine": "pc-q35-9.1",
    "bios": "ovmf",
    "agent": "1",
    "scsi0": "local-lvm:vm-100-disk-0,size=100G",
    "boot": "order=scsi0",
    "name": "win10-tian"
  },
  "connections": [
    {
      "key": "rdp",
      "label": "远程桌面 (RDP)",
      "target": "192.168.10.50:3389",
      "command": "mstsc /v:192.168.10.50",
      "open": true
    },
    {
      "key": "smb",
      "label": "共享文件夹 (SMB)",
      "target": "192.168.10.50:445",
      "command": "\\\\192.168.10.50",
      "open": true
    },
    {
      "key": "ping",
      "label": "Ping",
      "target": "192.168.10.50",
      "command": "ping 192.168.10.50",
      "open": true
    },
    {
      "key": "console",
      "label": "PVE 控制台 (VNC)",
      "target": "https://pve-1.home.arpa/?console=kvm&vmid=100&node=pve-1&resize=off",
      "command": "https://pve-1.home.arpa",
      "open": true,
      "external": true
    }
  ],
  "credentials": {
    "source": "console",
    "os": "windows",
    "accounts": [
      {
        "role": "管理员",
        "user": "idc",
        "password": "<Windows 管理员密码>",
        "note": "本地管理员账号（模板内置）"
      }
    ]
  },
  "history": [[1760000000, 24.1, 38.4]],
  "pve_link": "https://pve-1.home.arpa/?console=kvm&vmid=100&node=pve-1&resize=off"
}
```

顶层字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `vmid` / `name` / `status` / `template` / `node` | — | 基本信息 |
| `uptime` | int | 运行时长（秒） |
| `ip` | string \| null | 客户机 IP |
| `ostype` | string | PVE 配置的 ostype，如 `l26`、`win10` |
| `is_windows` | bool | `ostype` 是否以 `win` 开头 |
| `macs` | array | 网卡 MAC 列表，元素含 `if`、`mac`、`raw` |
| `agent` | object | QGA `get-osinfo` 结果；查询失败或未启用时为 `{}`。当前仅当 `config.agent` 以 `enabled` 开头才查询，`agent=1` 实际常为空对象 |
| `metrics` | object | 实时指标，字段同列表行 |
| `config` | object | PVE 配置子集（见下） |
| `connections` | array | 连接方式与端口探测结果 |
| `credentials` | object | 凭据登记/模板默认值 |
| `history` | array | 最近最多 90 个采样，`[ts, cpu_pct, mem_pct]` |
| `pve_link` | string | PVE 原生 VNC 控制台直链 |

`config` 可能包含：

`cores`、`sockets`、`memory`、`ostype`、`machine`、`bios`、`agent`、`onboot`、`description`、`tags`、`scsi0`、`ide2`、`boot`、`name`、`ciuser`。

其中 `machine` / `bios` 缺失时会填充默认说明字符串。

`connections` 元素：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | `rdp` / `smb` / `ssh` / `ping` / `console` |
| `label` | string | 展示名 |
| `target` | string | `IP`、`IP:端口` 或控制台 URL |
| `command` | string | 建议命令（`mstsc`、`ssh`、`ping`、`\\IP`） |
| `open` | bool | 端口探测是否开放；`console` 表示 VM 是否运行 |
| `external` | bool | 仅 `console` 出现，表示外部链接 |

- 仅当 VM 运行且有 IP 时，才返回 SSH/RDP/SMB/Ping 条目；`console` 始终返回，`open` 表示是否运行。
- Windows：`rdp`、`smb`、`ping`、`console`；Linux：`ssh`、`ping`、`console`。

`credentials` 结构：

```json
{
  "source": "console",
  "os": "linux",
  "accounts": [
    {
      "role": "root",
      "user": "root",
      "password": "<密码或 null>",
      "note": "SSH 密码登录已开启（也可用于 VNC）"
    },
    {
      "role": "SSH 公钥",
      "user": "root",
      "key": "ssh-ed25519 AAAA... user@host",
      "password": null,
      "note": "已写入该用户的 ~/.ssh/authorized_keys（cloud-init）"
    }
  ]
}
```

- `source`：`console`（控制台有登记）/ `template`（无登记但按模板/默认值展示，Windows 老机器也会落到这里）/ `unknown`（Linux 历史机器且无登记，且不是模板）。
- `accounts[]`：`role`、`user`、`password`、`note`；Linux 密钥账号额外有 `key`。
- **详情接口会返回明文虚拟机密码**，仅应提供给已授权管理员；Agent 不要写入日志或长期记忆。

错误：

- `404 {"detail":"虚拟机不存在"}`

### 5.3 模板列表

`GET /api/templates`

```json
{
  "templates": [
    {
      "vmid": 9001,
      "name": "debian-13-template",
      "label": "Debian 13",
      "cores": 2,
      "mem": 2147483648,
      "disk": 10737418240
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `vmid` | int | 模板 VMID |
| `name` | string | PVE 模板名 |
| `label` | string | 控制台显示名 |
| `cores` | int \| null | 模板 vCPU |
| `mem` | int | 模板内存（bytes） |
| `disk` | int | 模板系统盘大小（bytes） |

默认模板：

| VMID | 系统 |
|---|---|
| `9000` | Ubuntu 24.04 |
| `9001` | Debian 13 |
| `9014` | Windows 10 LTSC |

隐藏模板（默认 `9002` Win11 退役模板）不会出现在列表中。

### 5.4 创建虚拟机

`POST /api/clone`

请求示例（Linux，密码 + 密钥）：

```json
{
  "template_vmid": 9001,
  "name": "debian-web-01",
  "cores": 2,
  "memory_mb": 2048,
  "auth": "both",
  "ciuser": "root",
  "cipassword": "<Linux 密码>",
  "sshkeys": "ssh-ed25519 AAAA... user@host"
}
```

请求示例（Windows）：

```json
{
  "template_vmid": 9014,
  "name": "win10-app-01",
  "cores": 4,
  "memory_mb": 8192
}
```

字段：

| 字段 | 类型 | 必填 | 约束/说明 |
|---|---|---|---|
| `template_vmid` | int | ✅ | 必须是模板；`9000` / `9001` / `9014` |
| `name` | string | ✅ | 1–63 字符；正则 `[A-Za-z0-9][A-Za-z0-9-]{0,62}`，必须以字母/数字开头，只允许字母、数字、连字符 |
| `cores` | int \| null | | 1–32；不传沿用模板 |
| `memory_mb` | int \| null | | 512–131072；不传沿用模板 |
| `auth` | string | | **仅 Linux**：`password` / `key` / `both`（默认 `both`）；Windows 忽略 |
| `ciuser` | string \| null | | **仅 Linux**：cloud-init 用户名，最大 64；默认服务端 `LINUX_CIUSER`（当前 `root`） |
| `cipassword` | string \| null | | **仅 Linux**：明文密码，最大 128；不传则用服务端 `LINUX_CI_PASSWORD`；`auth=key` 时忽略 |
| `sshkeys` | string \| string[] \| null | | **仅 Linux**：一个或多个 OpenSSH 公钥；不传则用服务端 `LINUX_SSH_KEY`；`auth=password` 时忽略 |
| `start` | bool | | **兼容字段，已忽略**；创建后始终自动开机 |

`auth` 语义（Linux）：

| 值 | 密码 | 公钥 | sshd 密码登录 |
|---|---|---|---|
| `password` | 写入（请求值或默认值） | 清空克隆盘继承的 `authorized_keys` | 开机后开启 |
| `key` | 不写，并删除继承的 `cipassword` | 写入 | 不主动开启 |
| `both` | 写入 | 写入 | 开机后开启 |

> 若服务端默认密码/公钥为空，且请求也没有提供，则对应凭据不会写入。调用方应确保至少一种登录方式可用。
>
> Windows 不支持 cloud-init 凭据注入；管理员账号/密码取模板内置值（`WINDOWS_ADMIN_USER` / `WINDOWS_ADMIN_PASSWORD`），`auth`、`ciuser`、`cipassword`、`sshkeys` 对 Windows 忽略。

行为：

1. 校验名称、模板。
2. 取 PVE 下一个 VMID，登记“创建中”占位。
3. `full clone`，等待 PVE 任务完成（最长 600 秒）。
4. 应用 CPU/内存。
5. Linux：写入 cloud-init 凭据，清理未选中的登录方式。
6. **始终自动开机**（`POST .../status/start`）。
7. Linux 密码/两者模式：后台异步等待 QGA（最多 90 秒）后开启 sshd 密码登录。
8. 记录凭据到控制台数据库：Windows 必登记；Linux 仅在模板含 cloud-init 时登记。
9. 返回新 VMID 和凭据。

响应：

```json
{
  "ok": true,
  "vmid": 100,
  "name": "debian-web-01",
  "credentials": {
    "source": "console",
    "os": "linux",
    "accounts": [
      {
        "role": "root",
        "user": "root",
        "password": "<密码或 null>",
        "note": "SSH 密码登录已开启（也可用于 VNC）"
      },
      {
        "role": "SSH 公钥",
        "user": "root",
        "key": "ssh-ed25519 AAAA... user@host",
        "password": null,
        "note": "已写入该用户的 ~/.ssh/authorized_keys（cloud-init）"
      }
    ]
  }
}
```

> `credentials` 仅对 Windows 和含 cloud-init 的 Linux 模板登记为 `source="console"`；无 cloud-init 的 Linux 克隆可能返回 `source="unknown"`。

错误：

| 状态码 | 场景 |
|---|---|
| `400` | 名称不符合正则 |
| `404` | `template_vmid` 不存在或不是模板 |
| `502` | 克隆/配置/开机失败；`{"detail":"创建失败: ..."}` |
| `422` | 字段类型/范围/枚举校验失败 |

注意：

- 该接口是**阻塞**的：仅克隆任务就允许最长 600 秒，之后还有配置和开机请求；HTTP 客户端超时应至少 650 秒。
- **非幂等**：请求超时后不要盲目重试，先 `GET /api/vms` 按 `name` 查找是否已创建，避免重复机器。
- 若克隆成功但后续配置失败，可能残留一台未完成配置的 VM；按返回/列表中的 `vmid` 删除。
- 克隆期间 `/api/vms` 中可能出现 `status="creating"` 的占位行，或已被 PVE 列出但仍在创建中的行。

### 5.5 电源操作

`POST /api/vms/{vmid}/action`

请求：

```json
{"action": "start"}
```

允许值：

| 值 | 含义 |
|---|---|
| `start` | 开机 |
| `shutdown` | 优雅关机（ACPI） |
| `stop` | 强制停止 |
| `reboot` | 重启 |

成功：

```json
{"ok": true, "upid": "UPID:pve:..."}
```

说明：

- 对模板操作返回 `400`。
- VM 不存在返回 `404`。
- PVE 操作失败返回 `502 {"detail":"PVE 操作失败: ..."}`。
- 对已登记 Linux 密码登录的机器执行 `start` 时，服务端会异步重新应用 sshd 密码登录配置。

### 5.6 删除虚拟机

`DELETE /api/vms/{vmid}`

请求体：

```json
{"confirm_name": "debian-web-01"}
```

`confirm_name` 必须与当前 VM 名称完全一致，否则返回 `400`。

成功：

```json
{"ok": true, "vmid": 100}
```

行为：

- 模板受保护，返回 `400 {"detail":"模板受保护，不能删除"}`。
- 运行中的 VM 先强制 `stop`，最多等待约 40 秒。
- 然后 `purge=1` 删除，等待 PVE 任务（最长 120 秒）。
- 清理控制台凭据登记、IP 缓存和监控历史。

错误：

| 状态码 | 场景 |
|---|---|
| `400` | 模板、名称不匹配 |
| `404` | VM 不存在 |
| `502` | 停止/删除任务失败 |

> `DELETE` 带 JSON body 时，部分客户端/代理可能丢弃 body；使用 curl 时请显式加 `-X DELETE -H 'Content-Type: application/json' -d '...'`。

### 5.7 修改凭据

`POST /api/vms/{vmid}/credentials`

请求体（字段全部可选，但至少提供一个）：

```json
{
  "user": "root",
  "password": "<新密码>",
  "ssh_key": "ssh-ed25519 AAAA... user@host",
  "ssh_key_remove": "ssh-ed25519 AAAA... old@host",
  "enable_password_login": true
}
```

字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `user` | string \| null | 目标账号，最大 64；不传则用已登记账号；Linux 默认服务端 `LINUX_CIUSER`（当前 `root`），Windows 默认 `WINDOWS_ADMIN_USER`（当前 `idc`）；只允许 `[A-Za-z0-9._-]+` |
| `password` | string \| null | 新密码，最大 128；Linux 会同时开启 sshd 密码登录；Windows 通过 `net user` 修改 |
| `ssh_key` | string \| null | 追加 SSH 公钥，最大 4096；必须以 `ssh-` 或 `ecdsa-` 开头；仅 Linux |
| `ssh_key_remove` | string \| null | 精确移除 SSH 公钥，最大 4096；仅 Linux |
| `enable_password_login` | bool \| null | 显式开启/关闭 SSH 密码登录；仅 Linux；Windows 会忽略该字段，但仍会执行运行/agent 前置检查 |

> 注意：字段名是 `enable_password_login`，不是 `password_login`。传错字段会被忽略，最终可能返回 `400 {"detail":"没有需要修改的内容"}`。
>
> Windows 判定基于控制台凭据登记（`os="windows"`），不是实时读取 `ostype`；未登记的历史 Windows VM 可能按 Linux 分支处理。

前置条件：

- VM 必须存在且不是模板。
- VM 必须处于 `running` 状态；否则 `409 {"detail":"请先启动虚拟机（修改凭据需要 guest agent）"}`。
- QGA 必须就绪；否则 `409 {"detail":"guest agent 未就绪，请稍后重试"}`。

行为：

- Linux：
  - `password` → 设置密码，并开启 `PasswordAuthentication yes` / `PermitRootLogin yes`。
  - `ssh_key` → 追加到目标用户 `authorized_keys`。
  - `ssh_key_remove` → 从 `authorized_keys` 精确移除。
  - `enable_password_login` → 显式开关密码登录。
- Windows：
  - `password` → `net user "<user>" "<password>"`。
  - `ssh_key` / `ssh_key_remove` → `400 {"detail":"Windows 不支持 SSH 密钥"}`。
  - `enable_password_login` → 忽略。

成功：

```json
{
  "ok": true,
  "credentials": {
    "source": "console",
    "os": "linux",
    "accounts": [
      {
        "role": "root",
        "user": "root",
        "password": "<新密码>",
        "note": "SSH 密码登录已开启（也可用于 VNC）"
      }
    ]
  }
}
```

错误：

| 状态码 | 场景 |
|---|---|
| `400` | 模板、用户名不合法、没有可修改字段、Windows 传 SSH 字段、公钥格式不合法 |
| `404` | VM 不存在 |
| `409` | VM 未运行、guest agent 未就绪 |
| `422` | 字段超长/类型错误 |
| `502` | guest agent 执行失败；`{"detail":"修改凭据失败: ..."}` |

### 5.8 服务端默认凭据

`GET /api/defaults`

响应：

```json
{
  "linux": {
    "user": "root",
    "password": "<默认 Linux 密码或空字符串>",
    "ssh_key": "ssh-ed25519 AAAA... 或空字符串",
    "auth": "both"
  },
  "windows": {
    "user": "idc",
    "password": "<默认 Windows 管理员密码或空字符串>"
  }
}
```

说明：

- 仅登录管理员可访问。
- **该接口返回服务端默认密码的明文值**（不是打码值），用于新建表单预填；Agent 获取后不得写入日志/记忆。
- 默认值来自 `.env.local`：
  - `LINUX_CIUSER`
  - `LINUX_CI_PASSWORD`
  - `LINUX_SSH_KEY`
  - `WINDOWS_ADMIN_USER`
  - `WINDOWS_ADMIN_PASSWORD`
- 修改后需要重启服务。

---

## 6. 节点与日志

### 6.1 节点/存储概览

`GET /api/overview`

响应：

```json
{
  "node": {
    "name": "pve",
    "cpu": 18.5,
    "maxcpu": 28,
    "mem_used": 12000000000,
    "mem_total": 67000000000,
    "disk_used": 19500000000,
    "disk_total": 93900000000,
    "uptime": 1234567,
    "loadavg": ["1.25", "1.18", "1.31"],
    "pveversion": "pve-manager/9.1.1/42db4a6cf33dac83"
  },
  "counts": {
    "total": 6,
    "running": 2,
    "stopped": 0,
    "templates": 4
  },
  "storages": [
    {
      "name": "local-lvm",
      "type": "lvmthin",
      "used": 49100000000,
      "total": 1700000000000,
      "avail": 1600000000000
    }
  ],
  "ts": 1760000000
}
```

说明：

- `node.cpu` 已换算为百分比（PVE 原始值为 0..1 小数）。
- `node.mem_used` / `mem_total` 为节点内存（bytes）。
- `node.disk_used` / `disk_total` 是 PVE 系统盘 `/` 的口径；虚拟机磁盘在 `local-lvm` 等存储池，见 `storages`。
- `counts.total` 包含模板；`counts.stopped` 不含模板；`counts.templates` 为模板数量。
- `storages` 只包含启用中的存储。

### 6.2 审计日志

`GET /api/logs?limit=100`

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `limit` | int | `100` | 返回条数；按 id 倒序（最新在前） |

响应：

```json
{
  "logs": [
    {
      "ts": 1760000000.123,
      "actor": "admin",
      "action": "clone",
      "vmid": 100,
      "detail": "debian-web-01 <- tpl 9001 (2c/2048MB) +start",
      "ok": true
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `ts` | number | Unix 时间戳（浮点） |
| `actor` | string | 操作人 |
| `action` | string | `login` / `clone` / `delete` / `start` / `shutdown` / `stop` / `reboot` / `credentials` 等 |
| `vmid` | int \| null | 相关 VMID；登录等无 VM 的操作可能为 `null` |
| `detail` | string | 详情 |
| `ok` | bool | 是否成功 |

没有分页参数；`limit` 未做范围校验，负数会被 SQLite 视为无限制，日志量大时请使用正整数并取较小值。

---

## 7. Agent 工作流

以下示例使用 Python `requests`（`pip install requests`）。所有密码都从环境变量或密钥管理系统读取，示例中只写占位符。

### 7.1 登录并检查会话

```python
import os
import requests

BASE = "https://console.example.com"
s = requests.Session()

r = s.post(f"{BASE}/api/login", json={
    "username": "admin",
    "password": os.environ["PVE_CONSOLE_PASSWORD"],
}, timeout=15)
r.raise_for_status()

vms = s.get(f"{BASE}/api/vms", timeout=15).json()["vms"]
print([(v["vmid"], v["name"], v["status"]) for v in vms])
```

处理 `401`：重新登录一次；仍失败则停止，不要循环重试。

### 7.2 创建 Linux 虚拟机并等待可用

```python
import os
import time
import requests

BASE = "https://console.example.com"
s = requests.Session()
s.post(f"{BASE}/api/login", json={
    "username": "admin",
    "password": os.environ["PVE_CONSOLE_PASSWORD"],
}, timeout=15).raise_for_status()

payload = {
    "template_vmid": 9001,
    "name": "debian-web-01",
    "cores": 2,
    "memory_mb": 2048,
    "auth": "both",
    "ciuser": "root",
    "cipassword": os.environ["NEW_VM_PASSWORD"],
    "sshkeys": open(os.path.expanduser("~/.ssh/id_ed25519.pub")).read().strip(),
}

# 克隆是阻塞接口，超时必须 >= 650 秒
r = s.post(f"{BASE}/api/clone", json=payload, timeout=650)
r.raise_for_status()
vm = r.json()
vmid = vm["vmid"]
print("created", vmid)

# 轮询列表，直到不再是 creating
for _ in range(120):
    rows = s.get(f"{BASE}/api/vms", timeout=20).json()["vms"]
    row = next((x for x in rows if x["vmid"] == vmid), None)
    if row and row["status"] != "creating" and row.get("ip"):
        print("ready", row["ip"])
        break
    time.sleep(2)
else:
    raise TimeoutError("VM did not become ready")

detail = s.get(f"{BASE}/api/vms/{vmid}", timeout=20).json()
print(detail["ip"], detail["metrics"]["mem_pct"], detail["metrics"]["mem_source"])
```

Linux 登录：

- `auth=both/password`：后台等待 QGA（最多 90 秒）后开启 sshd 密码登录，建议轮询 SSH 端口。
- `auth=key`：直接用对应私钥 SSH。
- 连接命令可从详情的 `connections[]` 读取。

### 7.3 创建 Windows 虚拟机

```python
payload = {
    "template_vmid": 9014,
    "name": "win10-app-01",
    "cores": 4,
    "memory_mb": 8192,
}
r = s.post(f"{BASE}/api/clone", json=payload, timeout=650)
r.raise_for_status()
vmid = r.json()["vmid"]
```

等待 `status=running` 且有 IP 后：

- RDP：`mstsc /v:<ip>`
- SMB：`\\<ip>`
- 凭据：`GET /api/vms/{vmid}` → `credentials.accounts[0]`
- 内存：读取 `metrics.mem_pct` / `metrics.mem_source`
  - `guest`：真实值
  - `guest-unavailable`：显示“—”，不要当作 0 或 100

### 7.4 修改 Linux 密码/公钥

```python
r = s.post(f"{BASE}/api/vms/{vmid}/credentials", json={
    "password": os.environ["NEW_VM_PASSWORD"],
}, timeout=60)
r.raise_for_status()
print(r.json()["credentials"])
```

追加公钥：

```python
s.post(f"{BASE}/api/vms/{vmid}/credentials", json={
    "ssh_key": open(os.path.expanduser("~/.ssh/id_ed25519.pub")).read().strip(),
}, timeout=60).raise_for_status()
```

关闭密码登录（保留密钥）：

```python
s.post(f"{BASE}/api/vms/{vmid}/credentials", json={
    "enable_password_login": False,
}, timeout=60).raise_for_status()
```

### 7.5 删除虚拟机

```python
name = "debian-web-01"
r = s.request("DELETE", f"{BASE}/api/vms/{vmid}", json={
    "confirm_name": name,
}, timeout=180)
r.raise_for_status()
```

删除前建议再次 `GET /api/vms/{vmid}` 核对名称，避免误删。

---

## 8. 错误码速查

| 状态码 | 结构 | 常见原因 |
|---|---|---|
| `400` | `{"detail":"..."}` | 名称不合法、模板受保护、没有可修改字段、SSH 字段用于 Windows |
| `401` | `{"detail":"未登录"}` / `{"detail":"用户名或密码错误"}` | Cookie 缺失/过期、登录失败 |
| `404` | `{"detail":"虚拟机不存在"}` / `{"detail":"模板不存在"}` | VMID/模板不存在 |
| `409` | `{"detail":"请先启动虚拟机（修改凭据需要 guest agent）"}` / `{"detail":"guest agent 未就绪，请稍后重试"}` | 改凭据时 VM 未运行或 QGA 未就绪 |
| `422` | `{"detail":[...]}` | Pydantic 字段校验失败 |
| `502` | `{"detail":"PVE 连接失败: ..."}` / `{"detail":"创建失败: ..."}` / `{"detail":"PVE 操作失败: ..."}` / `{"detail":"删除失败: ..."}` / `{"detail":"修改凭据失败: ..."}` | PVE/上游任务失败（`/api/vms`、克隆、电源、删除、凭据、health 有包装；详情/模板/概览的 PVE 异常可能直接表现为 `500`） |

---

## 9. 已知限制与安全注意

1. **Windows 内存依赖 QGA**
   - QGA 不可用时返回 `guest-unavailable` / `mem_pct=null`，这是刻意设计，避免退回宿主 RSS 造成假 100%。
   - 需要 Windows 模板启用 `agent=1` 且 QGA 服务正常运行。

2. **Windows 凭据修改依赖 QGA**
   - 改密码需要 guest agent 在线；SSH 密钥接口对 Windows 不支持。

3. **克隆耗时**
   - PVE 克隆+开机最长约 600 秒；客户端超时应大于 650 秒。
   - 克隆非幂等；超时后先查列表，不要直接重试。

4. **列表首次查询可能较慢**
   - Windows 内存缓存 15 秒，冷缓存时 QGA 超时 6 秒；Agent 请求 `/api/vms` 建议 15 秒以上超时。

5. **会话**
   - 12 小时过期，无 refresh token；Agent 应处理 `401` 并重新登录。
   - Cookie 未设置 `Secure`；生产必须走 HTTPS。

6. **凭据暴露面**
   - `/api/vms/{vmid}` 和 `/api/defaults` 会返回明文密码，仅限已登录管理员。
   - Agent 不应把密码、Cookie 写入日志、聊天记录或长期记忆。

7. **无分页/无速率限制**
   - 日志只有 `limit`，没有 offset/分页；大量日志时请限制 `limit`。
   - 当前没有显式 API 限流，脚本应自行控制并发。

8. **无 API 版本前缀**
   - 路径为 `/api/...`，没有 `/v1`；升级可能带来不兼容变更，调用方应固定文档版本并做回归。

9. **部分查询接口未统一包装 PVE 异常**
   - `GET /api/vms/{vmid}`、`GET /api/templates`、`GET /api/overview` 未捕获 PVE 异常，可能返回 `500` 而不是 `502`；Agent 应同时处理 `500` 并重试/告警。

10. **详情 `agent` 字段的启用判定**
    - 当前仅在 `config.agent` 以 `enabled` 开头时查询 QGA；PVE 常见的 `agent=1` 会返回空对象，不影响内存/凭据使用。

11. **凭据接口的 Windows 判定**
    - `POST /api/vms/{vmid}/credentials` 用控制台登记的 `os` 判断 Windows；未登记的历史 Windows VM 会走 Linux 分支。

---

## 10. 端点与实现索引

| 端点 | 实现位置 |
|---|---|
| `POST /api/login` / `POST /api/logout` | `app/main.py` 登录/会话段 |
| `GET /api/vms` | `list_vms()` |
| `GET /api/vms/{vmid}` | `vm_detail()` |
| `GET /api/templates` | `templates()` |
| `POST /api/clone` | `clone_vm()` |
| `POST /api/vms/{vmid}/action` | `vm_action()` |
| `DELETE /api/vms/{vmid}` | `delete_vm()` |
| `POST /api/vms/{vmid}/credentials` | `update_credentials()` |
| `GET /api/defaults` | `defaults()` |
| `GET /api/overview` | `overview()` |
| `GET /api/logs` | `logs()` |
| `GET /api/health` | `health()` |
| `GET /` | `index()`（静态页面，不属于 JSON API） |

> 需要机器可读的完整 schema 时，直接请求 `GET /openapi.json`；本文档补充了 OpenAPI 不会表达的运行时语义（QGA 回退、创建中占位、克隆非幂等等）。
