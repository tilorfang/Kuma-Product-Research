# Kuma Product Research

亚马逊选品工具。Skill 通过网页读取卖家精灵网页版数据，从销量、核心关键词与搜索趋势、竞争、差评和利润等维度分析产品，生成可离线打开的 HTML 可视化报告及 Markdown 摘要。

推荐使用带内置浏览器或浏览器工具的 agent，例如 **Codex、Claude Code、Kimi Code**。各客户端的浏览器能力与安装方式不同，部分需要自行配置浏览器工具。也可接入各家数据 MCP 使用，默认不绑定任何 MCP 服务或账号。

## 安装与使用

下载本仓库，将整个目录命名为 `kuma-product-research`，放入所用 agent 的 skills 目录。例如 Codex 使用 `~/.codex/skills/kuma-product-research/`；其他客户端按其技能安装说明操作。重新加载技能后调用：

```text
$kuma-product-research 调研美国站 ASIN Bxxxxxxxxx，采购成本为人民币 25 元/套。
```

也可用“选品工具”等自然语言描述任务。

使用网页取数前，请自行登录卖家精灵并确保套餐有对应查询权限。成本未知也可完成市场分析；计算利润还需成本、装数、包装尺寸/重量及费用口径。

## 报告与演示

- 销量历史、竞品对比、关键词搜索趋势、差评与改良机会。
- 商品主图与商品页链接、来源记录、明确的数据缺口。
- “可推进 / 有机会推进 / 淘汰”判断及下一步，利润卡片内可展开本地计算器。

[下载并打开演示报告](examples/demo/report.html)。演示及测试全部使用**模拟数据和占位图**，不是实际调研或卖家精灵导出；演示 ASIN 仅用于展示链接格式。

## 数据与扩展

默认用卖家精灵网页，插件可用时互补，也接受其导出或截图。可选 MCP 由使用者自行配置和授权，需保留提供方、工具、站点、周期及父子体口径，不能冒称卖家精灵网页实查。详见 [MCP 接入约定](references/mcp.md)。本仓库不包含账号、密钥或一键安装数据 MCP 的配置。

## 本地运行

Python 3.10+；报告渲染和经济性计算仅用标准库。浏览器取数由运行 skill 的 agent 完成，以下脚本本身不负责登录或抓取。

```bash
python scripts/render_report.py --input examples/demo/research.json --out-dir outputs/demo
python -m unittest discover -s tests -v
```

计算方式及输入见 [经济性说明](references/economics.md)，报告字段见 [数据结构](references/report-schema.md)。

## 适用范围

计算器内置固 2026 年美国非服装参考费率，并非实时 Amazon 费用；其他站点需要有来源的费用覆盖和币种确认。默认汇率、头程、佣金、广告及退货比例是可编辑情景，未覆盖仓储、关税、认证、开模等全部成本。利润结果只作初筛参考。
