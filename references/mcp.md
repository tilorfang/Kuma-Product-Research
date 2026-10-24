# 可选 MCP 数据接入

默认渠道是卖家精灵网页版。使用者可在自己的 agent 中配置所需的数据 MCP；本技能不硬编码服务地址、密钥、工具名称，也不承诺兼容所有提供方。

1. 从当前环境发现实际可用的工具，检查授权、支持站点和字段。先用目标对象做一次真实查询，不把“连接已建立”当作已有数据。
2. 将结果归一化到 report-schema.md：保留 ASIN、父子体、规格、周期、单位、估算属性、采样范围及来源。不同来源冲突保留双方值，不平均或择高；不支持的字段保持缺失。
3. 每个 MCP 来源使用 `kind=mcp`，另填非空 `provider` 和 `tool`；其余字段与网页来源相同。`locator` 只存不含认证信息的记录定位，`raw_file` 指向运行目录内脱敏记录。
4. 数据 MCP 只能作实际返回字段的来源。业务输入仍为 `kind=user, role=business_input`，不得标为市场实查。网页、插件及 MCP 来源不得互相冒充。
5. 密钥由运行环境管理，不写入 skill、报告、示例、URL、导出或 Git。验证失败或权限受阻时说明缺口，继续可用模块，不自动安装服务或购买权限。

来源示例（仅结构演示，不是真实工具）：

```json
{"id":"M01","kind":"mcp","provider":"example-provider","tool":"example-product-query","name":"产品查询","locator":"normalized/mcp-record-01.json","retrieved":"2026-10-24","period":"2026-09","scope":"child","nature":"平台估算","raw_file":"raw/mcp-record-01.json"}
```

渲染器校验来源字段和引用关系，不负责调用 MCP；具体查询由 agent 使用当前环境真实工具完成。来源完整不等于数据可靠，仍需核对分析口径。
