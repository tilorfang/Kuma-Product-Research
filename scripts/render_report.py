"""Render continuous schema-3 research; retain schema-2 historical compatibility."""
import argparse
import hashlib
import html
import json
import re
import math
import base64
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from html.parser import HTMLParser
from research_sections import validate_research, content as research_content, markdown as research_markdown
from calculator_panel import panel as calculator_panel

VERDICT_ALIASES = {'继续验证':'可推进','待补证据':'有机会推进'}
VERDICTS = {'可推进','有机会推进','淘汰'} | set(VERDICT_ALIASES)
def is_market_source(source):
    return source.get('kind') in ('sellersprite_web','sellersprite_plugin','sellersprite_export','mcp')


COLORS = ['#146c68','#4d92a5','#8cabc1','#cc9a55','#a87790','#76849e','#bc604e']

def esc(value):
    if isinstance(value,(int,float,Decimal)) and not isinstance(value,bool):
        value=format(value,',')
    elif isinstance(value,str) and re.fullmatch(r'[-+]?\d{4,}(?:\.\d+)?',value) and not re.fullmatch(r'(?:19|20)\d{2}',value):
        whole,sep,fraction=value.partition('.')
        value=f'{int(whole):,}'+(sep+fraction if sep else '')
    return html.escape('待补' if value is None else str(value), quote=True)

def number(value, percent=False):
    if value is None:
        return '待补'
    return f'{value*100:.1f}%' if percent else f'{value:,.2f}'

def table(head, rows):
    if not rows:
        return '<div class="empty">暂无可用数据，见关键缺口。</div>'
    return '<div class="table"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def refs(item):
    return ' / '.join(item.get('source_ids',[]))

def evidence_detail(text='', source_ids=''):
    return ''

def verification_table(dimensions):
    by_name={x['name']:x for x in dimensions}
    rows=[]
    for name in ['需求','竞争','利润','落地风险']:
        x=by_name[name]
        stats='<br>'.join(esc(m['label'])+'：<strong>'+esc(m.get('value'))+'</strong>' for m in x.get('metrics',[])[:3]) or '待补'
        rows.append('<tr><th scope="row"><strong>'+esc(name)+'</strong></th><td>'+esc(x.get('conclusion',x.get('implication','还缺少资料，暂时无法判断。')))+evidence_detail(x.get('evidence',''),refs(x))+'</td><td>'+stats+'</td><td>'+esc(x.get('action','补齐关键数据后再判断。'))+'</td></tr>')
    return '<div class="table verification-table"><table><thead><tr><th>验证项</th><th>结论</th><th>关键指标</th><th>下一步</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


AMAZON_DOMAINS={'US':'amazon.com','UK':'amazon.co.uk','GB':'amazon.co.uk','DE':'amazon.de','CA':'amazon.ca','JP':'amazon.co.jp','FR':'amazon.fr','IT':'amazon.it','ES':'amazon.es','AU':'amazon.com.au','MX':'amazon.com.mx','BR':'amazon.com.br','AE':'amazon.ae','SA':'amazon.sa','IN':'amazon.in','NL':'amazon.nl','SE':'amazon.se','PL':'amazon.pl','BE':'amazon.com.be','TR':'amazon.com.tr','SG':'amazon.sg','IE':'amazon.ie'}


def product_url(asin, site):
    asin=str(asin).upper()
    if not re.fullmatch(r'[A-Z0-9]{10}',asin):
        raise ValueError('竞品ASIN需为10位字母数字，不含Markdown或URL')
    domain=AMAZON_DOMAINS.get(site.upper())
    if not domain:
        raise ValueError('请补充该站点的Amazon域名映射')
    return 'https://www.'+domain+'/dp/'+asin


ASIN_TEXT = re.compile(r'(?<![A-Za-z0-9])B[A-Z0-9]{9}(?![A-Za-z0-9])')


def link_asins(body, site, products=()):
    """Link visible ASIN text while preserving existing links and HTML attributes."""
    sites={p['asin']:p.get('site',site) for p in products}
    class Linker(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.parts=[]
            self.blocked=[]
        def handle_starttag(self, tag, attrs):
            self.parts.append(self.get_starttag_text())
            if tag in ('a','script','style','title','h1','h2','h3','h4','h5','h6'): self.blocked.append(tag)
        def handle_startendtag(self, tag, attrs): self.parts.append(self.get_starttag_text())
        def handle_endtag(self, tag):
            self.parts.append('</'+tag+'>')
            if self.blocked and self.blocked[-1]==tag: self.blocked.pop()
        def handle_data(self, text):
            if not self.blocked:
                text=ASIN_TEXT.sub(lambda m:'<a class="asin-link" href="'+esc(product_url(m[0],sites.get(m[0],site)))+'" target="_blank" rel="noopener noreferrer">'+m[0]+'</a>',text)
            self.parts.append(text)
        def handle_entityref(self, name): self.parts.append('&'+name+';')
        def handle_charref(self, name): self.parts.append('&#'+name+';')
        def handle_comment(self, text): self.parts.append('<!--'+text+'-->')
    parser=Linker();parser.feed(body);parser.close()
    return ''.join(parser.parts)


def thumbnail_sections(body, products, root, site="US"):
    """Add product context to ASINs in the three research sections only."""
    catalog={p['asin']:p for p in products}
    class Thumbnails(HTMLParser):
        def __init__(self):super().__init__(convert_charrefs=False);self.parts=[];self.stack=[];self.active=False;self.svg=0;self.heading=False
        def handle_starttag(self,tag,attrs):
            self.parts.append(self.get_starttag_text());attrs=dict(attrs)
            if tag=='section':self.active=False
            if tag=='svg':self.svg+=1
            if tag in ('h3','h4'):self.heading=True
            if tag=='a':self.stack.append(attrs)
        def handle_endtag(self,tag):
            self.parts.append('</'+tag+'>')
            if tag=='a' and self.stack:self.stack.pop()
            if tag=='svg':self.svg-=1
            if tag in ('h3','h4'):self.heading=False
            if tag=='section':self.active=False
        def handle_data(self,value):
            if value in ('销量历史与销售对比','竞争格局与价格带','差评主题与差异化机会'):self.active=True
            if self.active and self.stack and not self.svg and value in catalog:
                self.parts.append(product_image(catalog[value],root)+'<span>'+value+'</span>')
            elif self.active and self.heading and not self.stack:
                match=next((p for a,p in catalog.items() if a in value),None)
                if match:self.parts.append('<a class="heading-image" href="'+esc(product_url(match['asin'],match.get('site',site)))+'" target="_blank" rel="noopener noreferrer">'+product_image(match,root)+'</a>')
                self.parts.append(value)
            else:self.parts.append(value)
        def handle_entityref(self,name):self.parts.append('&'+name+';')
        def handle_charref(self,name):self.parts.append('&#'+name+';')
    parser=Thumbnails();parser.feed(body);return ''.join(parser.parts)


def sales_text(item):
    data=item.get('monthly_sales')
    if not data:
        return '待补'
    if not isinstance(data,dict):
        raise ValueError('monthly_sales必须标明口径、范围和周期')
    value=data.get('value')
    display=data.get('display')
    kind=data.get('kind','unknown')
    scope=data.get('scope','unknown')
    if value is not None:
        if kind not in ('estimate','actual') or not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<0:
            raise ValueError('只有非负数值估算或实售可作为月销量数值')
        display=integer(value)
    if display is None:
        return '待补'
    label={'estimate':'平台估算','actual':'实售','purchase_band':'购买提示，非精确月销','range':'区间，非精确月销'}.get(kind,'口径待核')
    prefix='' if scope=='child' else '本款待补；'+('父体参考：' if scope=='parent' else '范围待核：')
    return prefix+str(display)+'\n'+label+' · '+str(data.get('period','周期待核'))


def product_image(item, run_root=None):
    """Embed sourced local product images; never fetch URLs or escape the run directory."""
    name=item.get('image_file')
    if not name or run_root is None:
        return '<span class="product-image missing-image" role="img" aria-label="主图未获取">暂无主图</span>'
    path=(Path(run_root)/name).resolve()
    if not path.is_relative_to(Path(run_root).resolve()):
        raise ValueError('商品主图必须位于本次运行目录内')
    if not item.get('image_source_ids'):
        raise ValueError('商品主图须注明实际市场数据来源')
    raw=path.read_bytes()
    mime=None
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):mime='image/png'
    elif raw.startswith(b'\xff\xd8\xff'):mime='image/jpeg'
    elif raw[:6] in (b'GIF87a',b'GIF89a'):mime='image/gif'
    elif raw.startswith(b'RIFF') and raw[8:12]==b'WEBP':mime='image/webp'
    if mime is None:raise ValueError('主图须为PNG/JPEG/WebP/GIF位图')
    return '<img class="product-image" src="data:'+mime+';base64,'+base64.b64encode(raw).decode('ascii')+'" alt="'+esc(item.get('brand','')+' '+item['asin']+' 商品主图')+'" loading="lazy">'


def competitor_table(items, site, run_root=None):
    if not items:
        return table([],[])
    rows=[]
    for c in items:
        link='<a href="'+esc(product_url(c['asin'],c.get('site',site)))+'" target="_blank" rel="noopener noreferrer">'+esc(c['asin'])+'</a><small class="question">'+esc(c.get('brand',''))+'</small>'
        values=[c.get('spec',''),number(c.get('price_usd')),sales_text(c),c.get('reviews')]
        photo='<a class="product-image-link" href="'+esc(product_url(c['asin'],c.get('site',site)))+'" target="_blank" rel="noopener noreferrer">'+product_image(c,run_root)+'</a>'
        rows.append('<tr><td>'+link+'</td>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>')
    return '<div class="table competitor-table"><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in ['ASIN / 品牌','规格','整套售价 USD','月销量 / 近月提示','评论数'])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def coverage_view(items):
    if not items:
        return ''
    states={'available':'已取得','partial':'已有部分数据','not_queried':'尚未查询','no_data':'已查无返回','blocked':'取数受阻','not_applicable':'口径不适用'}
    rows=[[x.get('target',''),x['field'],states.get(x.get('status'),x.get('status')),x.get('available',''),x.get('next_action','')] for x in items]
    attempts='\n'.join(x['field']+'：'+json.dumps(x.get('attempts',[]),ensure_ascii=False) for x in items)
    return '<details><summary>取数覆盖与补充记录</summary>'+table(['对象','字段','完成情况','已有信息','下一步'],rows)+evidence_detail(attempts)+'</details>'


def gap_layout(gaps, actions):
    cards=[]
    for i,g in enumerate(gaps,1):
        if isinstance(g,str):
            g={'title':g}
        parts=[]
        for key,label in [('impact','影响判断'),('action','补充方式'),('owner','负责人'),('criterion','完成标准')]:
            if g.get(key): parts.append('<div><dt>'+label+'</dt><dd>'+esc(g[key])+'</dd></div>')
        cards.append('<article class="gap-item"><span class="gap-index">'+str(i).zfill(2)+'</span><div><h3>'+esc(g.get('title','待补数据'))+'</h3>'+('<dl>'+''.join(parts)+'</dl>' if parts else '')+'</div></article>')
    gap_body=''.join(cards) if cards else '<div class="empty">暂无关键数据缺口</div>'
    return '<div class="gap-layout"><div><h3>关键缺口 <span class="gap-count">'+str(len(gaps))+'</span></h3>'+gap_body+'</div><aside class="action-plan"><h3>推进动作</h3>'+listing(actions)+'</aside></div>'

def section(title, body):
    return '<section class="panel"><h2>'+esc(title)+'</h2>'+body+'</section>'

def listing(values):
    return '<ul>'+''.join('<li>'+esc(v)+'</li>' for v in values)+'</ul>' if values else '<p class="muted">无新增事项</p>'

def sources_view(sources):
    def rows(items):
        return table(['ID / 来源','定位 / 原始文件','日期 / 周期','范围 / 性质 / 限制'],[[f"{x['id']} · {x['name']}"+(' · '+x['provider']+' / '+x['tool'] if x['kind']=='mcp' else ''),f"{x.get('locator','')}\n{x.get('raw_file') or ''}",f"{x.get('retrieved','')} / {x.get('period','')}",f"{x.get('scope','')} / {x.get('nature','')}\n{x.get('notes','')} "] for x in items])
    market = [x for x in sources if is_market_source(x)]
    inputs = [x for x in sources if x['kind']=='user']
    parts = ['<details><summary>数据来源（展开查看）</summary>']
    if market:
        parts.append('<h3>市场数据来源</h3>'+rows(market))
    if inputs:
        parts.append('<details><summary>业务输入（成本 / 包装 / 报价）</summary>'+rows(inputs)+'</details>')
    return ''.join(parts)+'</details>'

def integer(value):
    return f"{Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP):,}"


def trend(data):
    points=data.get('points',[])
    valid=[p['value'] for p in points if p.get('value') is not None]
    signals=data.get('signals',[])
    def signal_scope(signal):
        scope=signal.get('scope','')
        scope={'child':'子体','parent':'父体','host':'主机','unknown':'范围待核','子体购买档位':'子体','父体参考':'父体'}.get(scope,scope)
        return scope+' / '+signal.get('period','')
    known=table(['商品','参考销量','统计范围'],[[x.get('subject',''),x.get('display') if x.get('display') is not None else 'N/A',signal_scope(x)] for x in signals]) if signals else ''
    if signals:known+='<p class="muted signal-note">N/A表示未获取到</p>'
    # Chart caveats remain in the evidence data; the heading identifies reference scope.
    note=''
    if not valid:
        heading='' if data.get('heading_shown') else '<h3>'+esc(data.get('label','暂无可用序列'))+'</h3>'
        return heading+known+('' if signals else '<div class="empty">尚无可用历史数据。</div>')
    if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 for v in valid):
        raise ValueError('销量和搜索量必须为非负有限数值；档位文本请放signals')
    high=max(valid) or 1
    rough=high/4
    magnitude=10**math.floor(math.log10(rough))
    tick_step=next(factor*magnitude for factor in (1,2,5,10) if factor*magnitude>=rough)
    tick_step=max(1,tick_step)
    axis_max=tick_step*math.ceil(high/tick_step)
    width=max(640,len(points)*76+80)
    left,right,top,bottom=58,width-22,30,166
    plot_height=bottom-top
    spacing=(right-left)/len(points)
    bar_width=min(28,spacing*.4)
    marks=['<text x="'+str(left)+'" y="14" class="chart-tick">'+esc(data.get('unit',''))+'</text>']
    for tick in range(int(round(axis_max/tick_step))+1):
        value=tick*tick_step
        y=bottom-value/axis_max*plot_height
        marks.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" class="chart-gridline"/><text x="{left-10}" y="{y+4:.2f}" text-anchor="end" class="chart-tick">{integer(value)}</text>')
    unit=data.get('unit','')
    for i,p in enumerate(points):
        value=p.get('value')
        x=left+spacing*(i+.5)
        label=str(p['date'])+'：'+('待补' if value is None else integer(value)+' '+unit)
        if value is None:
            marks.append(f'<text x="{x:.2f}" y="{bottom-10}" text-anchor="middle" class="chart-tick">待补</text>')
        else:
            height=value/axis_max*plot_height
            y=bottom-height
            marks.append(f'<g class="bar-mark" tabindex="0" role="img" aria-label="{esc(label)}"><title>{esc(label)}</title><rect x="{x-bar_width/2:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height:.2f}" rx="4" class="histogram-bar"/><text x="{x:.2f}" y="{y-9:.2f}" text-anchor="middle" class="bar-value">{integer(value)}</text></g>')
        marks.append(f'<text x="{x:.2f}" y="{bottom+27}" text-anchor="middle" class="chart-tick">{esc(p["date"])}</text>')
    axes=f'<path d="M{left} {top}V{bottom}H{right}" class="chart-axis"/>'
    chart='<div class="chart-scroll"><svg class="histogram" viewBox="0 0 '+str(width)+' 210" style="min-width:'+str(width)+'px" role="group" aria-label="'+esc(data.get('label','数据柱状图'))+'">'+axes+''.join(marks)+'</svg></div>'
    heading='' if data.get('heading_shown') else '<h3>'+esc(data.get('label',''))+'</h3>'
    return known+heading+chart


def validate(data):
    if data.get('schema_version')=='3.0':
        validate_research(data)
        legacy=dict(data,schema_version='2.0',stage='C',competitors=data['products'])
        validate(legacy)
        market_ids={s['id'] for s in data['sources'] if is_market_source(s)}
        def market_refs(obj):
            if isinstance(obj,dict):
                if any(x not in market_ids for x in obj.get('source_ids',[])):
                    raise ValueError('市场记录不可引用用户业务输入作为市场来源')
                for value in obj.values(): market_refs(value)
            elif isinstance(obj,list):
                for value in obj: market_refs(value)
        for key in ('products','sales_series','keywords','keyword_series','review_themes'):
            market_refs(data[key])
        return
    required = ['schema_version','title','site','date','scope','stage','branch','decision',
                'decision_scope','summary','dimensions','sources','gaps','risks','key_evidence','priority_action']
    for key in required:
        if key not in data:
            raise ValueError('缺少字段: '+key)
    if data['schema_version'] != '2.0' or data['decision'] not in VERDICTS:
        raise ValueError('需要schema 2.0及可推进/有机会推进/淘汰判断')
    if data['stage'] not in ('A','B','C') or data['branch'] not in ('mature','new_consumable'):
        raise ValueError('stage或branch无效')
    if not data['decision_scope'] or not data['priority_action']:
        raise ValueError('必须说明阶段决策范围和唯一优先行动')
    if {x['name'] for x in data['dimensions']} != {'需求','竞争','利润','落地风险'} or len(data['dimensions']) != 4:
        raise ValueError('需要四项判断，可标明尚未验证')
    for row in data['dimensions']:
        if not row.get('conclusion') or not row.get('action') or len(row.get('metrics',[])) > 3:
            raise ValueError('每项须有通俗结论、下一步及最多3个指标')
    if len(data['key_evidence']) > 3:
        raise ValueError('摘要最多三个关键证据')
    ids = [s['id'] for s in data['sources']]
    if len(ids) != len(set(ids)):
        raise ValueError('重复来源ID')
    for s in data['sources']:
        if s['kind'] not in ('sellersprite_web','sellersprite_plugin','sellersprite_export','mcp','user'):
            raise ValueError('只接受卖家精灵、已配置MCP来源和用户业务输入')
        if s['kind']=='mcp' and (not s.get('provider') or not s.get('tool')):
            raise ValueError('MCP来源须记录provider和tool')
        if s['kind'] == 'user' and s.get('role') != 'business_input':
            raise ValueError('user仅用于business_input，不能充当市场数据源')
        for key in ('name','locator','retrieved','period','scope','nature','raw_file'):
            if key not in s:
                raise ValueError('来源缺少字段: '+key)
    def check_refs(obj):
        if isinstance(obj,dict):
            for ref in obj.get('source_ids',[]):
                if ref not in ids:
                    raise ValueError('无法解析来源: '+ref)
            for child in obj.values():
                check_refs(child)
        elif isinstance(obj,list):
            for child in obj:
                check_refs(child)
    check_refs(data)
    for evidence in data['key_evidence']:
        if not evidence.get('text') or not evidence.get('source_ids'):
            raise ValueError('关键证据须有正文和来源')
    for c in data.get('competitors',[]):
        product_url(c['asin'],c.get('site',data['site']))
        sales_text(c)
        monthly = c.get('monthly_sales')
        if monthly and (not monthly.get('period') or not monthly.get('source_ids')):
            raise ValueError('竞品销量须有周期和来源')
    for item in data.get('coverage',[]):
        if item['status'] not in ('available','partial','not_queried','no_data','blocked','not_applicable'):
            raise ValueError('未知coverage状态')
        if item['status']=='no_data' and not item.get('attempts'):
            raise ValueError('只有实际查询后才能标无数据')
    sales = data.get('sales',{})
    if any(p.get('value') is not None for p in sales.get('points',[])):
        if sales.get('scope') != 'child' or sales.get('kind') not in ('estimate','actual'):
            raise ValueError('本款数值销量图必须明确子体及估算/实售，父体/档位放signals')
        if not sales.get('source_ids') or not sales.get('subject'):
            raise ValueError('本款销量须注明对象和来源')
    # Validate chart values even when only Markdown is requested.
    for key in ('sales','demand'):
        trend(data.get(key,{}))


def economics_view(profit):
    if profit is None:
        return '<p>本阶段尚未验证经济性；没有采购成本不妨碍机会初筛，不能据此认定已盈利。</p>'
    metrics = [('整套售价','price_usd',False),('利润','profit_usd',False),('利润率','margin',True)]
    details = [('整套采购','procurement_usd',False),('头程','freight_usd',False),('FBA','fba_usd',False),
               ('佣金','commission_usd',False),('广告情景费用','advertising_usd',False),('退货损耗','returns_usd',False),
               ('固定FBA假设下盈亏平衡价','breakeven_price_fixed_fba_usd',False)]
    body = '<p>整套采购成本：¥'+number(profit.get('cost_set_cny'))+'；装数：'+esc(profit.get('quantity'))+'</p>'
    body += table(['关键指标','金额 USD / 比例'],[[label,number(profit.get(key),pct)] for label,key,pct in metrics])
    if profit['status'] == 'ceiling_estimate':
        body = '<div class="warn">采购上限情景估算；成本尚未知，利润未验证。</div>'+body
    elif profit['status'] == 'needs_data':
        body = '<div class="warn">计算待补：'+esc(' / '.join(profit.get('missing',[])))+'</div>'+body
    if 'max_set_cost_cny' in profit:
        body += '<p>目标利润率 '+number(profit['target_margin'],True)+' 下整套采购成本上限：¥'+number(profit['max_set_cost_cny'])+'；单件上限：¥'+number(profit['max_unit_cost_cny'])+'（负值表示该售价和费用下无法达到目标）。</p>'
    body += '<details><summary>计算明细与假设</summary>'+table(['指标','金额 USD / 比例'],[[label,number(profit.get(key),pct)] for label,key,pct in details])+listing(profit.get('assumptions',[]))
    if profit.get('fba_reference'):
        body += '<p>内置FBA参考：$'+number(profit['fba_reference'].get('total_usd'))+'；采用来源：'+esc(profit.get('fba_source',''))+'</p>'
    return body+'</details>'


def gap_text(gap):
    if isinstance(gap,str):
        return gap
    return gap.get('title','')+'；'+gap.get('impact','')+'；'+gap.get('action','')


def visible_limits(data, profit):
    lines = list(data['risks'])
    lines += [gap_text(g) for g in data['gaps'] if isinstance(g,str) or g.get('critical',True)]
    for x in data.get('coverage',[]):
        if x.get('critical',False) and x['status'] not in ('available','not_applicable'):
            lines.append(x['field']+'：'+x.get('decision_impact',x.get('next_action','当前判断所需证据尚不完整。')))
    if profit and profit['status']=='needs_data':
        lines.append('经济性输入未齐：'+' / '.join(profit.get('missing',[])))
    return list(dict.fromkeys(lines))


def report_gaps(data):
    gaps = list(data['gaps'])
    titles = {g if isinstance(g,str) else g.get('title','') for g in gaps}
    for item in data.get('coverage',[]):
        if item.get('critical',False) and item['status'] not in ('available','not_applicable') and item['field'] not in titles:
            gaps.append({'title':item['field'], 'impact':item.get('decision_impact','影响当前阶段判断'),
                         'action':item.get('next_action','补充该项证据后复核。')})
    return gaps


def render(input_path, out_dir, include_html=None):
    input_path, out_dir = Path(input_path).resolve(), Path(out_dir).resolve()
    root = input_path.parent
    data = json.loads(input_path.read_text(encoding='utf-8-sig'))
    validate(data)
    data['decision']=VERDICT_ALIASES.get(data['decision'],data['decision'])
    modern=data['schema_version']=='3.0'
    if include_html is None:
        include_html=modern and data['mode']=='standard'
    mode_label=('标准分析' if data.get('mode')=='standard' else '简要分析')+' · '+('资料齐备' if data.get('research_status')=='completed' else '部分资料待补') if modern else '阶段 '+data['stage']
    dependencies = [input_path]
    for source in data['sources']:
        if source.get('raw_file'):
            raw = (root/source['raw_file']).resolve()
            if raw.is_relative_to(root) and raw.is_file():
                dependencies.append(raw)
    for product in data.get('products',data.get('competitors',[])):
        if product.get('image_file'):
            product_image(product,root)
            image_ids=product.get('image_source_ids',[])
            market_ids={s['id'] for s in data['sources'] if is_market_source(s)}
            if any(i not in market_ids for i in image_ids):raise ValueError('主图须引用已核实的市场来源')
            dependencies.append((root/product['image_file']).resolve())
    def load_profit(name):
        path = (root/name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('计算文件必须在运行目录内')
        dependencies.append(path)
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if value.get('status') not in ('ok','needs_data','ceiling_estimate'):
            raise ValueError('未知计算状态')
        return value
    profit = load_profit(data['profit_file']) if data.get('profit_file') else None
    scenarios = [(s,load_profit(s['profit_file'])) for s in data.get('scenarios',[])]
    limits = visible_limits(data,profit)
    out_dir.mkdir(parents=True,exist_ok=True)
    # Explicitly refuse to leave a stale HTML alongside a newer Markdown-only result.
    if not include_html and (out_dir/'report.html').exists():
        raise ValueError('目录已有HTML；请用新版本目录，或显式添加--html同步更新')
    def cell(value):
        return str(value).replace('|','\\|').replace('\n','<br>')
    md = ['# '+data['title'],'']
    if data.get('demo'):
        md += ['**演示数据，非市场结论。**','']
    md += [data['site']+' · '+data['date']+' · '+mode_label,'',
           '**'+data['decision']+'**：'+data['summary'],'',
           '判断范围：'+data['decision_scope'],'','研究边界：'+data['scope'],'']
    if limits:
        md += ['<details><summary><strong>当前判断的限制</strong></summary>','']+['- '+line for line in limits]+['','</details>','']
    md += ['| 验证项 | 结论 | 关键指标 | 下一步 |','|---|---|---|---|']
    by_name = {x['name']:x for x in data['dimensions']}
    for name in ('需求','竞争','利润','落地风险'):
        x = by_name[name]
        stats = '；'.join(m['label']+'：'+str(m.get('value','待补')) for m in x.get('metrics',[])) or '未验证'
        md.append('| '+' | '.join(cell(v) for v in (name,x['conclusion'],stats,x['action']))+' |')
    md += ['','**关键证据**','']+['- '+x['text']+'（'+refs(x)+'）' for x in data['key_evidence']]
    if not data['key_evidence']:
        md += ['尚无可支持市场判断的有效证据。']
    if profit:
        if profit['status']=='ok':
            md += ['','计算结果：利润 $'+number(profit.get('profit_usd'))+'；利润率 '+number(profit.get('margin'),True)+'。']
        elif profit['status']=='ceiling_estimate':
            md += ['','采购上限情景：目标利润率 '+number(profit['target_margin'],True)+'，整套 ¥'+number(profit['max_set_cost_cny'])+' / 单件 ¥'+number(profit['max_unit_cost_cny'])+'；采购成本及利润仍未知。']
        md += ['','<details><summary>计算与假设</summary>','',economics_view(profit)]
        for s,p in scenarios:
            md += ['',s['name']+'：利润 $'+number(p.get('profit_usd'))+' / 利润率 '+number(p.get('margin'),True)]
        md += ['','</details>']
    if modern:
        md += research_markdown(data)
    md += ['','**唯一优先下一步**：'+data['priority_action'],'',
           '<details><summary>依据与数据来源</summary>','']
    md += [x['name']+'：'+x.get('evidence','尚未验证')+'（'+refs(x)+'）' for x in data['dimensions']]
    md += ['']+[f"- {s['id']} [{s['kind']}] {s['name']} / {s['locator']} / {s['retrieved']} / {s['period']} / {s['scope']} / {s['nature']}" for s in data['sources']]
    md += ['',coverage_view(data.get('coverage',[])),'','</details>']
    markdown_text='\n'.join(md)
    # Existing Markdown links and source URLs already have destinations.
    protected=re.compile(r'(\[[^\]]*\]\([^\n)]*\)|https?://[^\s<>]+)')
    chunks=protected.split(markdown_text)
    for i in range(0,len(chunks),2):
        chunks[i]='\n'.join(line if re.match(r'^#{1,6}\s',line) else ASIN_TEXT.sub(lambda m:'['+m[0]+']('+product_url(m[0],data['site'])+')',line) for line in chunks[i].split('\n'))
    (out_dir/'report.md').write_text(''.join(chunks),encoding='utf-8')
    generated = [out_dir/'report.md']
    if include_html:
        economic_html = economics_view(profit)
        if scenarios:
            economic_html += table(['情景','利润 USD','利润率'],[[s['name'],number(p.get('profit_usd')),number(p.get('margin'),True)] for s,p in scenarios])
        report = section('四项快速验证',verification_table(data['dimensions']))+section('经济性与压力情景',economic_html)
        report += section('关键缺口与推进动作',gap_layout(report_gaps(data),[data['priority_action']])+coverage_view(data.get('coverage',[])))+sources_view(data['sources'])
        toggle='<button type="button" class="calculator-toggle" aria-controls="profit-calculator" aria-expanded="false">计算器</button>'
        kpi_items=[]
        has_profit=False
        for k in data.get('kpis',[]):
            is_profit=k['label'] in ('基准情景利润','预估利润 / 利润率')
            has_profit|=is_profit
            kpi_items.append('<article class="card'+(' profit-kpi' if is_profit else '')+'">'+(toggle if is_profit and modern else '')+'<small>'+esc('预估利润 / 利润率' if is_profit else k['label'].replace('评分数','评价数'))+'</small><div class="number">'+esc(k.get('value'))+'</div><small>'+esc(k.get('unit',''))+'</small></article>')
        if modern and not has_profit:
            value='$'+number(profit.get('profit_usd'))+' / '+number(profit.get('margin'),True) if profit and profit['status']=='ok' else '未获取到'
            kpi_items.append('<article class="card profit-kpi">'+toggle+'<small>预估利润 / 利润率</small><div class="number">'+value+'</div><small>当前成本与费用情景</small></article>')
        kpis='<div class="kpis">'+''.join(kpi_items)+'</div>'
        comps = competitor_table(data.get('competitors',[]),data['site'],root)
        if data.get('competitors'):
            comps += evidence_detail('\n'.join(c['asin']+'：'+c.get('reason','')+' / '+refs(c) for c in data['competitors']))
        dashboard = kpis+section('搜索量',trend(data.get('demand',{})))+section('销量',trend(data.get('sales',{})))+section('直接竞品对比',comps)
        bars = ''
        if profit and profit['status']=='ok':
            costs = [(label,profit[key]) for label,key in [('采购','procurement_usd'),('头程','freight_usd'),('FBA','fba_usd'),('佣金','commission_usd'),('广告','advertising_usd'),('退货','returns_usd')]]
            total = sum(v for _,v in costs)
            bars = '<p>费用构成（合计100%，非售价占比）</p><div class="bar">'+''.join(f'<span style="width:{v/total*100 if total else 0:.4f}%;background:{COLORS[i]}"></span>' for i,(_,v) in enumerate(costs))+'</div><div class="legend">'+''.join(f'<span><i class="dot" style="background:{COLORS[i]}"></i>{esc(label)} ${number(v)}</span>' for i,(label,v) in enumerate(costs))+'</div>'
        dashboard += section('费用与经济性',bars+economic_html)+sources_view(data['sources'])
        header = ('<div class="warn">演示数据 · 非市场调查结论</div>' if data.get('demo') else '')
        target=next((p for p in data.get('products',[]) if p.get('role')=='target'),None)
        target_photo='<a class="hero-product" href="'+esc(product_url(target['asin'],target.get('site',data['site'])))+'" target="_blank" rel="noopener noreferrer">'+product_image(target,root)+'</a>' if target else ''
        reasons=data.get('decision_reasons',[])
        reason_html='<div class="hero-reasons"><h3>主要原因</h3>'+listing(reasons)+'</div>' if reasons else ''
        header += '<header><div class="eyebrow">KUMA PRODUCT RESEARCH · '+esc(data['site'])+' · '+esc(data['date'])+' · '+esc(mode_label)+'</div><div class="hero-title">'+target_photo+'<div><h1>'+esc(data['title'])+'</h1><span class="verdict'+(' verdict-reject' if data['decision']=='淘汰' else '')+'">'+esc(data['decision'])+'</span></div></div><div class="hero-conclusion"><h3>先说结论</h3><p class="hero-summary">'+esc(data['summary'])+'</p></div>'+reason_html+'<div class="hero-scope"><h3>目前能推进到哪</h3><p>'+esc(data['decision_scope'])+'</p></div></header>'
        # Public header: visible regardless of active tab or collapsed disclosures.
        if limits:
            header += '<details class="warn limits"><summary><strong>当前判断的限制</strong></summary>'+listing(limits)+'</details>'
        header += '<p class="priority-action"><strong>唯一优先下一步：</strong>'+esc(data['priority_action'])+'</p>'
        tabs = '<nav role="tablist" aria-label="报告视图"><button id="tab-dashboard" role="tab" aria-selected="true" aria-controls="dashboard">可视化面板</button><button id="tab-report" role="tab" aria-selected="false" tabindex="-1" aria-controls="report">精简报告</button></nav>'
        scope = '<details class="scope-details"><summary>调研范围与说明</summary><p>'+esc(data['scope'])+'</p></details>'
        body = header+tabs+'<div id="dashboard" role="tabpanel" aria-labelledby="tab-dashboard">'+dashboard+'</div><div id="report" role="tabpanel" aria-labelledby="tab-report" hidden>'+report+'</div>'+scope
        if modern:
            inputs={}
            if data.get('calculator_input_file'):
                ip=(root/data['calculator_input_file']).resolve()
                if not ip.is_relative_to(root):raise ValueError('计算器输入须在运行目录内')
                dependencies.append(ip);inputs=json.loads(ip.read_text(encoding='utf-8-sig'))
            defaults=dict(quantity=1,fx=7,cost_basis='unit',package_basis='set',transport='sea',rate_cny_kg=12,divisor=6000,season='off',commission_pct=15,returns_pct=5,advertising_model='percent',advertising_pct=20,fuel_mode='on')
            defaults.update(inputs)
            defaults['fuel_mode']='off' if inputs.get('fuel') is False else 'on'
            defaults['site']=data['site']
            calc=calculator_panel(data,defaults,esc) if data['site']=='US' else '<section id="profit-calculator" class="panel" hidden>此简化计算器采用美国参考费率；其他站点请使用有来源费用的正式计算。</section>'
            body=header+kpis+calc+research_content(data,(esc,table,trend,section,refs,evidence_detail,lambda items,site:competitor_table(items,site,root)))
            body+=section('利润与压力情景',economic_html)
            body+=section('四项判断',verification_table(data['dimensions']))
            body+=section('关键缺口与下一步',gap_layout(report_gaps(data),[data['priority_action']]))
            body+=sources_view(data['sources'])+coverage_view(data.get('coverage',[]))+scope
            body+='<details><summary>执行记录与覆盖</summary>'+table(['模块','状态','耗时秒','页面访问','尝试与限制'],[[k,m['status'],m.get('elapsed_seconds'),m.get('page_visits'),'；'.join(m.get('attempts',[]))+'；'+m.get('reason','')] for k,m in data['module_status'].items()])+'</details>'
        template_path = Path(__file__).resolve().parents[1]/'assets/report.html'
        dependencies.append(template_path)
        template = template_path.read_text(encoding='utf-8-sig')
        body=link_asins(body,data['site'],data.get('products',data.get('competitors',[])))
        if modern:body=thumbnail_sections(body,data['products'],root,data['site'])
        page = template.replace('@@TITLE@@',esc(data['title'])).replace('@@BODY@@',body)
        if modern:
            page=page.replace('评分数','评价数').replace('购买档位','销量').replace('购买提示','销量提示').replace('待补','未获取到')
            js_paths=[Path(__file__).resolve().parents[1]/'assets'/name for name in ('calculator.js','calculator-ui.js')]
            dependencies+=js_paths
            page=page.replace('</body>','<script>'+''.join(p.read_text(encoding='utf-8') for p in js_paths)+'</script></body>')
        (out_dir/'report.html').write_text(page,encoding='utf-8')
        generated.append(out_dir/'report.html')
    files = list(dict.fromkeys(dependencies+generated))
    def manifest_path(path):
        for prefix,base in (('run',root),('output',out_dir),('skill',Path(__file__).resolve().parents[1])):
            if path.is_relative_to(base):
                return prefix+'/'+path.relative_to(base).as_posix()
        raise ValueError('清单依赖必须位于运行、输出或技能目录内')
    manifest = {'schema_version':data['schema_version'],'generated_for':data['date'],'outputs':[p.name for p in generated],
                'files':[{'path':manifest_path(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (out_dir/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return out_dir/('report.html' if include_html else 'report.md')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--out-dir',required=True,type=Path)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--html',dest='html',action='store_const',const=True,default=None,help='生成离线HTML')
    group.add_argument('--markdown-only',dest='html',action='store_const',const=False,help='仅生成Markdown摘要')
    args = parser.parse_args()
    print(render(args.input,args.out_dir,args.html))

