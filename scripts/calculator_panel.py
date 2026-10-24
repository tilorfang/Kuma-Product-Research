"""Offline calculator UI with explicit packaged-set inputs."""
import json
import html

def panel(data, inputs, esc):
    def num(key,label):
        value=inputs.get(key)
        return '<label>'+label+'<input type="number" step="any" name="'+key+'" value="'+html.escape('' if value is None else str(value),quote=True)+'"></label>'
    def select(key,label,options):
        return '<label>'+label+'<select name="'+key+'">'+''.join('<option value="'+v+'"'+(' selected' if inputs.get(key)==v else '')+'>'+text+'</option>' for v,text in options)+'</select></label>'
    def group(title,content):
        return '<fieldset class="calc-group"><legend>'+title+'</legend><div class="calc-fields">'+content+'</div></fieldset>'
    body='<section id="profit-calculator" class="panel calculator-panel" hidden><div class="calc-heading"><h2>运费与利润计算器</h2><button type="button" class="calc-close">收起</button></div><form class="profit-form">'
    packaging=''.join(num(k,label) for k,label in [('weight_kg','包装重量 · KG'),('length_cm','包装长 · CM'),('width_cm','包装宽 · CM'),('height_cm','包装高 · CM')])
    packaging+=select('package_basis','包装口径',[('set','整套实包'),('unit','单件包装（宽和重×件数）')])+num('quantity','每套件数')
    packaging+=select('transport','运输方式',[('sea','海运'),('air','空运'),('express','快递')])+num('rate_cny_kg','运费单价 · 元/KG')+num('divisor','材积重除数')+num('fx','汇率 · CNY/USD')
    body+=group('01  包装信息与运输设置',packaging)
    fba=num('price_usd','整套售价 · USD')+select('season','淡旺季费率',[('off','淡季'),('peak','旺季')])+select('fuel_mode','燃油附加费',[('on','开启 3.5%'),('off','关闭')])+num('special_usd','特殊处理费 · USD（适用时）')
    body+=group('02  FBA配送费（美国站）',fba)
    body+='<details class="calc-advanced"><summary>FBA覆盖值与来源（可选）</summary><div class="calc-fields">'+num('fba_override_usd','FBA覆盖 · USD')+'<label>FBA覆盖来源<input name="fba_override_source" value="'+esc(inputs.get('fba_override_source',''))+'"></label></div></details>'
    profit=num('unit_cost_cny','采购成本 · CNY')+select('cost_basis','成本口径',[('unit','单件'),('set','整套')])+num('commission_pct','佣金 · %')+num('returns_pct','退货损耗 · %')
    profit+=select('advertising_model','广告情景',[('percent','按售价比例'),('bid_cvr','建议竞价 / 假设转化率')])+num('advertising_pct','广告预算 · %')+num('suggested_bid_usd','建议竞价 · USD（非实际CPC）')+num('conversion_rate_pct','假设转化率 · %')
    body+=group('03  利润情景',profit)
    body+='<div class="calc-actions"><button type="submit">计算</button><button type="button" class="calc-reset">恢复原输入</button></div><div class="calc-summary" hidden aria-live="polite">'+''.join('<div><small>'+label+'</small><strong data-result="'+key+'">—</strong></div>' for key,label in [('freight','头程运费 · USD'),('fba','FBA · USD'),('profit','预估利润 · USD'),('margin','利润率')])+'</div><output class="calc-result" aria-live="polite">填写成本和包装后计算。</output>'
    body+='<details class="calc-notes"><summary>计算口径与适用范围</summary><p>包装尺寸按所选口径计算。V17固定2026美国非服装费率；未覆盖仓储、关税、认证、开模。修改结果为本地情景，不改原始调研结论。</p></details></form></section>'
    return body
