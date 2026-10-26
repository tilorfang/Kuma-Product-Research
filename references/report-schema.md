# 同源研究底稿（schema 3.0）

标准分析默认输出report.html、report.md和manifest.json。HTML为连续研究页；不再使用双页签。mode=brief默认Markdown，--html可补HTML，--markdown-only显式只输出文字。渲染器保留schema 2.0读取能力仅用于历史兼容；新研究必须用3.0，不把旧数据改个版本号冒充重新调查。

## 根字段

schema_version="3.0"；title/site/date/scope；mode=standard/brief；research_status=completed/partial；branch=mature/new_consumable；decision=可推进/有机会推进/淘汰；decision_scope/summary/priority_action；sources/risks/gaps/key_evidence/dimensions。不再要求stage。

四行dimensions：name为需求/竞争/利润/落地风险；conclusion/action为通俗分析；metrics最多3项label/value；evidence/source_ids。key_evidence最多3项text/source_ids，为摘要而非完整证据数量上限。

默认数组均存在，可空但须对应真实缺口：products、sales_series、keywords、keyword_series、review_themes、opportunities。每个市场记录带source_ids，只可引用卖家精灵或已核实的MCP市场来源。示例数据结构见tests/fixtures/standard-research.json（全部为合成测试数据，不得用作市场事实）。

## 产品与销量

products[]字段：asin、role(target/competitor/host/reference)、parent_asin（未知null）、brand、spec（装数和适配）、price_usd、reviews（页面评价数须注明）、rating、listed_at、segment（头部/中腰部/新品/异常/待核）、comparison_group、reason、source_ids。产品分组以可比规格为准，不靠品牌或大类。非美元价格先有来源和转换口径，否则price_usd=null。

monthly_sales为对象：value或display、kind(estimate/actual/purchase_band/range)、scope(child/parent/unknown)、period、source_ids。档位只有display，不填value。父体参考不能画为目标子体。

sales_series[]：subject=products中ASIN、label、unit、period、scope、kind、source_ids、points、signals、note。points=[{date:"2026-09",value:123}]；未知null，禁止数值字符串/NaN/负数/重复周期。parent/host数值序列必须reference_only=true并在独立面板醒目标明，不混进子体横向比较。unknown/purchase_band不可填数值points。档位历史用signals=[{subject,display,scope,period,note,source_ids}]原文展示。

上市时间与更早历史冲突：原记录保留，选择可解释观察窗；报告指出冲突，不能推断本款上市前销量。完整月/近30天/未完月分开。横向数值销量图仅比较相同period/kind/comparison_group的子体；父体/档位在表格保留。

## 关键词

keywords[]：keyword原文、category(核心/功能/场景/型号兼容/品牌等)、relevance（具体相关性）、monthly_searches（null或非负数）、period、suggested_bid_usd（可null）、source_ids。统计月未显示如实注明，不编造。不同周期分图，重叠词不求和。

keyword_series[]：subject=已登记keyword，scope=keyword，kind=estimate，label/unit/period/source_ids，points与销量相同。多词合并为一张月搜索量折线图，图号映射关键词原文，图表带整数标签、轴及悬停值。不能从截图曲线猜精确点数；只能读到曲线时保存截图并文字说明走势和限制。

## 评价与机会

review_themes[]：id、asin、scope(child/parent/mixed/unknown)、theme、category(设计/材质/制造/兼容/物流/使用误解等)、count、sample_size、sampling（日期/星级/变体/去重）、counting_rule、evidence_level(review_text/platform_summary)、finding、source_ids、quotes。

count/sample_size均非负整数，分母>0、count<=sample_size；若平台不提供可靠分母，两者null，不凑比例。每主题每条评价只计一次，同一评论可多主题，因此合计比例可超过100%。采样比例不是售后率。平台AI摘要按platform_summary处理，不能把其推测当原文证实。

quotes=[{text:短原文,review_id:页面ID或本地导出行号,source_ids:[...]}]；原文证据须有引文。可加日期/星级/译文，不能编造原文或用产品低评分替代原因。

opportunities[]：title、evidence_level（评价证实的痛点/可行性推测/有待样品验证）、theme_ids、source_ids、hypothesis、difficulty、validation。声称评价证实时必须链接真实主题。insights[]可选：finding/source_ids/hypothesis/validation，跨模块关联解释与待验证假设分开。

## 覆盖与效率

module_status为sales/keywords/competition/reviews/economics五键对象，各含status、attempts字符串数组、reason、finding、elapsed_seconds、page_visits。status=available/partial/blocked/no_data/not_queried/not_applicable。partial/blocked/no_data有真实路径和原因。标准模式前四项必须attempts且不得not_queried/not_applicable；任何不足整体partial。completed还需实有关键词、销量/搜索历史与评价数据，渲染器校验不能替代分析者质量检查。

耗时和访问数未知null，解释原因；不编造记录。coverage沿用细字段target/field/critical/status/available/attempts/next_action/decision_impact/source_ids；取数状态详细表折叠，首页只展示关键限制。

## 来源与经济性

sources每项id/kind/name/locator/retrieved/period/scope/nature/raw_file/notes。kind为sellersprite_web/sellersprite_plugin/sellersprite_export/mcp，或user且role=business_input；mcp另须provider和tool，适配说明见mcp.md。原始记录保存字段单位、对象、时间、周期、父子体、估算性质。认证信息不进入locator。user只作报价/成本/包装输入。

profit_file为运行目录内计算结果相对路径或null。scenarios=[{name,profit_file,source_ids}]，只能引用实际计算结果。成本上限显示情景和利润未知；广告不重复扣减。kpis=[{label,value,unit,source_ids}]由分析者明确口径，渲染器不凭缺失值推算。

gaps为{title,impact,action,critical}或文字；risks为重要风险文字；不重复堆满首屏。priority_action唯一优先动作。原始数据、计算输入及报告使用manifest哈希留档。只渲染不等于实际市场调查完成。

## 展示约定

不输出“查看依据”控件，来源与审计信息保留在底稿及统一折叠来源区。正文、表格、图表标签中的ASIN链接到对应站点商品页；h1–h6大小标题中的ASIN不加链接；已有链接不嵌套。表头加粗。图表移除重复note与caption说明，父体/主机参考仍在标题明确标注，单位在坐标与悬停保留。图表约210px高、最大820px宽，柱宽最多28px；长序列水平滚动。

“当前判断的限制”使用默认收起的details，展开可读原有内容。数量、评价数、搜索量、金额等大数值使用千位分隔符；日期、标识符不格式化。关键词表保留各词近月值；历史趋势统一为多折线图，同月悬停展示各搜索词及对应值（取整、千位分隔）。不同单位不合轴，缺失值显示待补且断线，不从未知历史编造点数。没有历史的关键词保留在表格，不用近月值伪造历史线。


## 商品主图和结论排版

products可加image_file（本次运行目录内相对路径，如raw/images/B0....jpg）和image_source_ids（实际卖家精灵来源ID）。只能保存实际页面/导出的对应规格主图，遵循当前浏览器下载能力；不能为凑图猜链接。渲染器支持PNG/JPEG/WebP/GIF，嵌入data URI以支持离线，禁止路径越界及SVG/HTML，图片纳入manifest。没有图显示占位，主图可点击商品页。

summary用一句自然、易懂的选品结论；可加decision_reasons字符串数组，2–3条说明关键事实和影响。decision_scope说明目前支持推进到哪一步。事实、推测与未验证保持明确，不用口语化掩盖不确定性。来源、范围、执行记录、限制等details统一白底圆角卡片。档位表scope简写child→子体、parent→父体；显示“子体 / 2026-02”。不重复输出“未知/不转换数值”等行说明，表下统一“N/A表示未获取到”；底稿保留原始口径与notes。


报告展示更新：购买档位在界面中统一称“销量”，保留原始档位、父子体范围及估算属性，不转精确数值；档位表列名“参考销量”。关键词相关性保留底稿，报告隐藏该列；缺失显示“未获取到”。标题主图链接商品页；销量、竞争、差评模块在ASIN旁显示已取得的对应主图，大小标题的ASIN文字仍不链接。产品名与“子体销量”之间加“ | ”。

利润卡片名“预估利润 / 利润率”，右上角“计算器”按钮展开位于销量模块之前的离线简化框。calculator_input_file可引用运行目录内实际利润输入JSON以预填，缺成本与包装保持空白；默认汇率/头程/广告预算为可编辑情景。仅美国使用内置固定参考费率；其他站点不套用。单件包装按宽及重量乘装数，整套实包不重复乘。广告两模式互斥，FBA覆盖需来源，缺特殊处理费不硬算。交互结果不覆盖原研究底稿与正式计算。正式利润仍由Python确定性计算器留档。


本次展示约定：商业判断使用“可推进 / 有机会推进 / 淘汰”；可推进仍须说明验证方案与投入边界，有机会推进须交代机会及缺口，均不表示直接采购批准。淘汰徽标黑底白字。历史数据中的旧判断值可由渲染器映射至新名称，不改历史证据。评分数统一显示为“评价数”，底稿reviews字段仍保留实际来源计数类型，rating count不得声称为文字评论条数。

利润与评分等KPI共享卡片高度、标签/数值/说明的排布，计算器按钮不单独撑高利润卡片。计算器展开沿用参考工具的白色圆角分区、居中输入、青色结果值：01包装信息与运输设置、02 FBA配送费、03利润情景；高级覆盖及适用范围折叠。广告两种口径仍互斥，计算公式不变。

差评按ASIN合并为一张商品卡片，卡头只展示一次商品主图和ASIN，各主题为卡内小节；每个主题保留各自的父子体/变体范围、日期/采样口径、命中数及样本分母和原文，不跨样本相加、不用主题数推断商品故障率。跨产品差异化机会仍单独汇总。
