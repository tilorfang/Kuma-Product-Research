# 运费和经济性计算

需要验证经济性时读取。V17固定2026美国非服装FBA参考表独立保存在 economics.py，不依赖其他工程。它不是实时费率；采用卖家精灵已核费用时使用有来源的覆盖值并保留参考差异。非US不套美国表。

## 输入模式

共同必填：`site`、`price_usd`（整套）、`quantity`（正整数装数）、`fx`（人民币/美元）、`weight_kg`、`length_cm`、`width_cm`、`height_cm`、`season`（off/peak）。缺项返回 needs_data，不用零补齐。

- `mode=profit`（默认）：另需 `unit_cost_cny`。已知真实成本才计算利润。
- `mode=cost_ceiling`：无需采购成本，另需明确 `target_margin_pct`（0–100）。只返回采购上限情景，status=ceiling_estimate，profit_usd/margin/procurement_usd保持null。不要填0采购成本来模拟此模式。
- `cost_basis=unit/set`（默认unit）。unit成本乘装数；set表示输入已是整套，不再乘。
- `package_basis=unit/set`（默认set）。优先整套实包。unit多件装按V17假设重量和宽乘n、长高不变，输出假设提示；不可称实测包装。
- 结果币种USD，采购上限CNY。售价/费用换算及汇率来源须在底稿明示，6.7仅可作显式假设。

运输 `transport=sea/air/express`：默认海运12 CNY/kg、体积除数6000；空运55/5000。可覆盖 `rate_cny_kg`、`divisor`，快递必须提供二者。均为可改的初筛假设。

佣金 `commission_pct=15`、退货 `returns_pct=5` 为预算默认，不代表已核平台费用。旺季参考10/15–1/14，由预计销售/入仓时间选，不直接等同取数日期。`fuel=true`默认3.5%；需要但未知的特殊费 `special_usd=null` 时不能给确定利润。

`fba_override_usd` 需同时给 `fba_override_source`；非US必须覆盖，且 `usd_conversion_confirmed=true` 确认售价及费用已转USD。覆盖值含哪些附加费应说明，不能再重复扣FBA。

## 广告模式（二选一）

| advertising_model | 输入 | 单套广告费用 |
|---|---|---|
| percent（默认） | advertising_pct，默认20 | 售价×预算比例 |
| bid_cvr | suggested_bid_usd、conversion_rate_pct | 建议竞价÷假设转化率 |

bid_cvr中 conversion_rate_pct=10 表示10%，须在(0,100]；建议竞价>=0。使用bid_cvr不能同时提供advertising_pct；percent也不能带竞价/转化率输入，计算器拒绝混合。建议竞价不是实际CPC，计算结果是情景广告费用，不是实际广告支出。实际CPC未知则原始记录保持null。

## 公式

计费重=max(实重,L×W×H/体积除数)；头程USD=计费重×人民币运价/fx，向上取美分。FBA另用英寸/磅、139体积除数及最小尺寸规则，不复用头程体积重。

令P=整套售价、C=整套采购美元、H=头程、D=FBA、c=佣金比例、r=退货比例、A=单套广告费：

- 利润=P−C−H−D−P×c−A−P×r；利润率=利润/P，不称完整财务净利。
- 目标利润率m的整套采购上限人民币=[P×(1−c−r−m)−A−H−D]×fx；单件上限=整套上限/装数，负值保留。
- percent下固定FBA盈亏平衡价=(C+H+D)/(1−c−r−a)，a为广告比例。
- bid_cvr下盈亏平衡价=(C+H+D+A)/(1−c−r)，假设建议竞价和转化率不随售价变动。
- 分母<=0时盈亏平衡价null。FBA随售价档变化，跨$10/$50必须重算，不能称精确盈亏平衡售价。

金额用Decimal计算，展示才舍入。仓储、关税、认证、开模等未覆盖，报告必须说明；有其他费用需明确扩展口径，不能暗改算法。标准模式有充分输入时分别跑降价、头程与广告压力情景（参数为明示假设），原输入和结果分别留档。

