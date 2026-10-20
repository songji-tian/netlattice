# 一句话部署

把下面任意一句交给 Agent：

> 看 https://github.com/songji-tian/netlattice ，并根据项目内容部署。

或本地版：

> 读 `AGENTS.md`，按 `topology.yaml` 部署。缺的密钥问我，危险操作先确认。

Agent 应自行完成：

1. 读 `AGENTS.md` 和 `topology.yaml`
2. 跑 `preflight` 和 `validate_topology.py`
3. 给出 `plan`
4. 只询问缺失的密钥
5. 按 `dns → vpn → compute` 顺序执行
6. 逐项验证并交报告

不要一上来就 `docker compose up`。
