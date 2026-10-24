"""Schema 3 validation and continuous offline research sections (no network)."""
import math
import json

LINE_COLORS=('#146c68','#c16c36','#5267b5','#9a4880','#428bb2','#7b8935','#995c39','#775dc1','#317e5c','#bd5353','#54707d','#a78323')


def keyword_lines(d, esc):
    """Align monthly keyword histories without filling missing values or joining gaps."""
    series=[s for s in d['keyword_series'] if s.get('points')]
    if not series:
        return '<div class="empty">暂无可用搜索量历史；当前词量见关键词表。</div>'
    # Different units must never share a numeric axis.
    units={s['unit'] for s in series}
    if len(units)>1:
        return '<div class="empty">搜索趋势单位不一致，需统一口径后合并展示。</div>'
    dates=sorted({p['date'] for s in series for p in s['points']})
    values=[p['value'] for s in series for p in s['points'] if p.get('value') is not None]
    if not values:
        return '<div class="empty">搜索量历史暂缺，未将缺失值补零。</div>'
    width=max(760,len(dates)*64+110)
    left,right,top,bottom=72,width-22,25,195
    high=max(values) or 1
    rough=high/4
    mag=10**math.floor(math.log10(rough))
    step=max(1,next(f*mag for f in (1,2,5,10) if f*mag>=rough))
    ceiling=step*math.ceil(high/step)
    spacing=(right-left)/max(len(dates)-1,1)
    def x(i):return (left+right)/2 if len(dates)==1 else left+i*spacing
    def y(v):return bottom-v/ceiling*(bottom-top)
    def integer(v):return f'{math.floor(v+.5):,}'
    marks=['<text x="'+str(left)+'" y="14" class="chart-tick">'+esc(next(iter(units)))+'</text>']
    for n in range(int(round(ceiling/step))+1):
        v=n*step;yy=y(v)
        marks.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{right}" y2="{yy:.2f}" class="chart-gridline"/><text x="{left-10}" y="{yy+4:.2f}" text-anchor="end" class="chart-tick">{integer(v)}</text>')
    legend=[];lookups=[]
    for i,s in enumerate(series):
        color=LINE_COLORS[i%len(LINE_COLORS)]
        lookup={p['date']:p.get('value') for p in s['points']};lookups.append(lookup)
        legend.append('<span><i class="dot" style="background:'+color+'"></i>'+esc(s['subject'])+'</span>')
        segment=[]
        def flush():
            if segment:marks.append('<polyline fill="none" stroke="'+color+'" stroke-width="2.5" points="'+' '.join(segment)+'"/>')
            segment.clear()
        for j,date in enumerate(dates):
            v=lookup.get(date)
            if v is None:flush();continue
            segment.append(f'{x(j):.2f},{y(v):.2f}')
            marks.append(f'<circle cx="{x(j):.2f}" cy="{y(v):.2f}" r="3.5" fill="{color}"/>')
        flush()
    marks.append(f'<path d="M{left} {top}V{bottom}H{right}" class="chart-axis"/>')
    for j,date in enumerate(dates):
        rows=[{'keyword':s['subject'],'value':None if lookup.get(date) is None else integer(lookup[date]),'color':LINE_COLORS[i%len(LINE_COLORS)]} for i,(s,lookup) in enumerate(zip(series,lookups))]
        tip=esc(json.dumps({'date':date,'unit':next(iter(units)),'rows':rows},ensure_ascii=False))
        fallback=date+'\n'+'\n'.join(row['keyword']+'：'+(row['value'] or '待补') for row in rows)
        hit_width=min(spacing, right-left) if len(dates)>1 else right-left
        hit_left=max(left,x(j)-hit_width/2);hit_right=min(right,x(j)+hit_width/2)
        marks.append(f'<g class="line-hit" tabindex="0" role="img" aria-label="{esc(fallback)}" data-tip="{tip}"><title>{esc(fallback)}</title><rect x="{hit_left:.2f}" y="{top}" width="{hit_right-hit_left:.2f}" height="{bottom-top}" fill="transparent"/><line x1="{x(j):.2f}" y1="{top}" x2="{x(j):.2f}" y2="{bottom}" class="line-guide"/></g>')
        marks.append(f'<text x="{x(j):.2f}" y="{bottom+25}" text-anchor="middle" class="chart-tick">{esc(date)}</text>')
    return '<h3>月搜索量趋势</h3><div class="keyword-chart"><div class="legend">'+''.join(legend)+'</div><div class="chart-scroll"><svg class="keyword-lines" viewBox="0 0 '+str(width)+' 240" style="min-width:'+str(width)+'px" role="group" aria-label="各关键词月搜索量趋势">'+''.join(marks)+'</svg></div><div class="line-tooltip" role="status" hidden></div></div>'

MODULES=('sales','keywords','competition','reviews','economics')
STATES=('available','partial','blocked','no_data','not_queried','not_applicable')

def numeric(v, label, integer=False):
    if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (integer and int(v)!=v)):
        raise ValueError(label+'须为非负有限数值或null')

def validate_research(d):
    for key in ('mode','research_status','products','sales_series','keywords','keyword_series','review_themes','opportunities','module_status'):
        if key not in d: raise ValueError('schema 3.0缺少: '+key)
    if d['mode'] not in ('standard','brief') or d['research_status'] not in ('completed','partial'):
        raise ValueError('研究模式/完成状态无效')
    modules=d['module_status']
    if set(modules)!=set(MODULES): raise ValueError('需要五个模块的取数状态')
    for name,m in modules.items():
        if m.get('status') not in STATES: raise ValueError('模块状态无效')
        if m['status'] in ('blocked','no_data','partial') and (not m.get('attempts') or not m.get('reason')):
            raise ValueError('受阻/部分数据须记录实际尝试与原因')
        for key in ('elapsed_seconds','page_visits'): numeric(m.get(key),key,key=='page_visits')
    if d['mode']=='standard':
        for name in MODULES[:4]:
            m=modules[name]
            if m['status'] in ('not_queried','not_applicable') or not m.get('attempts'):
                raise ValueError('标准模式必须尝试销量、关键词、竞争和评价')
        if d['research_status']=='completed' and any(modules[x]['status']!='available' for x in MODULES[:4]):
            raise ValueError('标准研究关键模块未齐，不能标完成')
    ids=[p['asin'] for p in d['products']]
    if len(ids)!=len(set(ids)): raise ValueError('产品ASIN重复')
    if not any(p.get('role')=='target' for p in d['products']): raise ValueError('缺目标产品')
    for p in d['products']:
        if p.get('role') not in ('target','competitor','host','reference'): raise ValueError('产品角色无效')
        for k in ('rating','reviews','price_usd'): numeric(p.get(k),k,k=='reviews')
        if p.get('rating') is not None and p['rating']>5: raise ValueError('评分不得超过5')
        if not p.get('source_ids'): raise ValueError('产品须有来源')
    words=[k['keyword'] for k in d['keywords']]
    if len(words)!=len(set(words)): raise ValueError('关键词重复')
    for k in d['keywords']:
        for key in ('monthly_searches','suggested_bid_usd'): numeric(k.get(key),key)
        if not all(k.get(x) for x in ('category','relevance','period','source_ids')): raise ValueError('关键词须有分类、相关性、周期和来源')
    for field in ('sales_series','keyword_series'):
        for s in d[field]:
            if not all(s.get(x) for x in ('subject','source_ids','period','unit','label','scope','kind')): raise ValueError('趋势须有对象、来源、周期、单位和口径')
            if s['subject'] not in (ids if field=='sales_series' else words): raise ValueError('趋势对象未登记')
            if field=='sales_series' and s['scope'] not in ('child','parent','host','unknown'): raise ValueError('销量范围无效')
            if field=='keyword_series' and (s['scope']!='keyword' or s['kind']!='estimate'): raise ValueError('搜索趋势须标关键词估算')
            dates=[p['date'] for p in s.get('points',[])]
            if len(dates)!=len(set(dates)): raise ValueError('趋势周期重复')
            for p in s.get('points',[]): numeric(p.get('value'),'趋势值')
            values=any(p.get('value') is not None for p in s.get('points',[]))
            if values and (s['kind'] not in ('estimate','actual') or s['scope']=='unknown'): raise ValueError('档位或未知范围不得画数值柱')
            if field=='sales_series' and s['scope'] in ('parent','host') and not s.get('reference_only'): raise ValueError('父体/主机须明确仅参考')
    themes=[t['id'] for t in d['review_themes']]
    if len(themes)!=len(set(themes)): raise ValueError('主题ID重复')
    for t in d['review_themes']:
        if t.get('asin') not in ids or not all(t.get(x) for x in ('theme','category','source_ids','sampling','counting_rule','evidence_level')): raise ValueError('评价主题缺对象、抽样及计数口径')
        if t.get('scope') not in ('child','parent','mixed','unknown'): raise ValueError('评价须标父子体/混合范围')
        n,N=t.get('count'),t.get('sample_size')
        numeric(n,'主题命中数',True); numeric(N,'评价样本量',True)
        if (n is None)!=(N is None) or (N is not None and (N==0 or n>N)): raise ValueError('主题计数与样本分母不成立')
        if t['evidence_level'] not in ('review_text','platform_summary'): raise ValueError('评价证据类型无效')
        if t['evidence_level']=='review_text' and not t.get('quotes'): raise ValueError('原文证据需要可追溯短摘录')
        for q in t.get('quotes',[]):
            if not all(q.get(x) for x in ('text','review_id','source_ids')): raise ValueError('评论引文需要ID与来源')
    for o in d['opportunities']:
        if not all(o.get(x) for x in ('title','evidence_level','hypothesis','difficulty','validation')): raise ValueError('机会须区分证据、假设及验证')
        if o['evidence_level'] not in ('评价证实的痛点','可行性推测','有待样品验证'): raise ValueError('机会证据等级无效')
        if any(t not in themes for t in o.get('theme_ids',[])): raise ValueError('机会引用未知主题')
        if o['evidence_level']=='评价证实的痛点' and not o.get('theme_ids'): raise ValueError('评价痛点必须引用主题')
    if d['research_status']=='completed' and d['mode']=='standard':
        if not d['keywords'] or not d['sales_series'] or not d['keyword_series'] or not d['review_themes']:
            raise ValueError('无趋势/关键词/评价证据不能标标准研究完成')
        if not any(any(p.get('value') is not None for p in s.get('points',[])) or s.get('signals') for s in d['sales_series']):
            raise ValueError('空销量序列不算历史证据')
        if not any(any(p.get('value') is not None for p in s.get('points',[])) for s in d['keyword_series']):
            raise ValueError('空搜索序列不算历史证据')

def content(d, api):
    esc,table,trend,section,refs,detail,comps=api
    def note(key):
        m=d['module_status'][key]
        msg=m.get('finding','')
        if m['status']!='available': msg+='\n本模块资料不完整：'+m.get('reason','尚未核实')
        return '<p class="finding">'+esc(msg)+'</p>'
    def series(items):
        blocks=[]
        for s in items:
            label=s['label']
            label=label.replace('购买档位','销量')
            if s.get('scope')=='child':
                for suffix in ('子体销量','子体估算销量'):
                    if suffix in label and '| '+suffix not in label:label=label.replace(suffix,' | '+suffix)
            if s.get('reference_only'): label+=' · '+('父体参考' if s['scope']=='parent' else '主机参考')+'，非目标子体销量'
            chart=dict(s,label=label,heading_shown=True)
            blocks.append('<article class="series-card"><h3>'+esc(label)+'</h3>'+trend(chart)+'</article>')
        return ''.join(blocks) or '<div class="empty">未取得可展示的历史序列；具体尝试见证据记录。</div>'
    products=d['products']
    comparable=[p for p in products if p.get('role') in ('target','competitor')]
    sales=note('sales')+series(d['sales_series'])
    groups={}
    for p in comparable:
        m=p.get('monthly_sales') or {}
        if m.get('scope')=='child' and m.get('kind') in ('actual','estimate') and m.get('value') is not None:
            groups.setdefault((m['period'],m['kind'],p.get('comparison_group',p['asin'])),[]).append(p)
    for (period,kind,group),ps in groups.items():
        sales+=trend({'label':'近月销量对比 · '+group+' · '+kind+' · '+period,'unit':'件/套（按产品口径）','source_ids':list(dict.fromkeys(r for p in ps for r in p['monthly_sales']['source_ids'])),'points':[{'date':p['asin'],'value':p['monthly_sales']['value']} for p in ps]})
    kw=note('keywords')
    # Separate periods and units rather than comparing inconsistent windows.
    for period in dict.fromkeys(k['period'] for k in d['keywords']):
        ks=[k for k in d['keywords'] if k['period']==period]
        kw+=table(['图号 / 关键词','需求类别','月搜索量','统计周期','建议竞价 USD（非CPC）'],[[str(i+1)+' · '+k['keyword'],k['category'],None if k.get('monthly_searches') is None else round(k['monthly_searches']),k['period'],k.get('suggested_bid_usd')] for i,k in enumerate(ks)])
    kw+=keyword_lines(d,esc)
    competition=note('competition')+comps(comparable,d['site'])
    competition+=table(['样本','评分','上架时间','样本定位','比较边界'],[[p['asin'],p.get('rating'),p.get('listed_at'),p.get('segment','待核'),p.get('reason','')] for p in comparable])
    review=note('reviews')
    if not d['review_themes']: review+='<div class="empty">尚无可核实的评价主题；不能仅凭低评分推测原因。</div>'
    # One product card per ASIN; preserve each theme's scope and denominator.
    for asin in dict.fromkeys(t['asin'] for t in d['review_themes']):
        product=next((p for p in products if p['asin']==asin),{})
        identity=' · '.join(str(x) for x in (product.get('brand'),product.get('spec')) if x)
        review+='<article class="review-card" data-asin="'+esc(asin)+'"><h3>'+esc(asin)+'</h3>'
        if identity:review+='<p class="muted">'+esc(identity)+'</p>'
        for t in (t for t in d['review_themes'] if t['asin']==asin):
            ratio='未提供可靠计数' if t.get('count') is None else str(t['count'])+'/'+str(t['sample_size'])+' 条有效样本（非订单故障率）'
            scope={'child':'子体评价','parent':'父体评价样本','mixed':'混合变体样本','unknown':'变体范围待核'}[t['scope']]
            review+='<div class="review-theme"><h4>'+esc(t['theme'])+'</h4><p class="review-meta">'+esc(scope+' · '+t['category']+' · '+ratio)+'</p><p>'+esc(t.get('finding',''))+'</p>'
            for q in t.get('quotes',[]): review+='<blockquote>'+esc(q['text'])+'<small> — '+esc(q['review_id'])+' · '+esc(refs(q))+'</small></blockquote>'
            review+=detail(t['sampling']+'；'+t['counting_rule']+'；'+t['evidence_level'],refs(t))+'</div>'
        review+='</article>'
    review+=table(['差异化方向','证据等级','可行性推测','难度','样品/后续验证'],[[o['title'],o['evidence_level'],o['hypothesis'],o['difficulty'],o['validation']] for o in d['opportunities']]) if d['opportunities'] else '<p>现有证据不足以提出经过验证的差异化方向。</p>'
    insights=d.get('insights',[])
    if insights:
        review+=table(['交叉发现','依据','假设（非事实）','验证方法'],[[x['finding'],' / '.join(x.get('source_ids',[])),x.get('hypothesis',''),x.get('validation','')] for x in insights])
    return section('销量历史与销售对比',sales)+section('关键词需求与搜索趋势',kw)+section('竞争格局与价格带',competition)+section('差评主题与差异化机会',review)

def markdown(d):
    lines=['','## 多维度研究','']
    for name,title in zip(MODULES,('销量与历史','关键词需求','竞争格局','评价与差异化','经济性')):
        m=d['module_status'][name]
        lines+=['### '+title,'',m.get('finding','尚无充分结论'),'','覆盖：'+m['status']+'；'+m.get('reason',''),'']
    lines+=['| 关键词 | 类别 | 月搜索量 | 周期 |','|---|---|---|']
    def cell(v):
        if isinstance(v,(int,float)) and not isinstance(v,bool):v=format(v,',')
        return str('未知' if v is None else v).replace('|','\\|').replace('\n',' ')
    for k in d['keywords']: lines.append('| '+' | '.join(cell(k.get(x)) for x in ('keyword','category','monthly_searches','period'))+' |')
    for asin in dict.fromkeys(t['asin'] for t in d['review_themes']):
        lines+=['','### '+asin+' 评价主题','','| 主题 | 评价范围 | 命中/有效样本 | 证据 |','|---|---|---|---|']
        for t in (t for t in d['review_themes'] if t['asin']==asin):
            quotes='；'.join(q['text']+'（'+q['review_id']+'）' for q in t.get('quotes',[]))
            scope={'child':'子体','parent':'父体','mixed':'混合变体','unknown':'范围未核'}[t['scope']]
            lines.append('| '+' | '.join(cell(x) for x in (t['theme'],scope,str(t.get('count'))+'/'+str(t.get('sample_size')),quotes))+' |')
    for o in d['opportunities']: lines+=['','- '+o['title']+'（'+o['evidence_level']+'）：'+o['hypothesis']+'；难度：'+o['difficulty']+'；验证：'+o['validation']]
    return lines
