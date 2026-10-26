"""Independent Decimal implementation of the user's freight/profit model."""
import argparse
import json
from decimal import Decimal as D, ROUND_CEILING
from pathlib import Path

SMALL = [
    [[2.43,3.32,3.58],[2.49,3.42,3.68],[2.56,3.45,3.71],[2.66,3.54,3.80],[2.77,3.68,3.94],[2.82,3.78,4.04],[2.92,3.91,4.17],[2.95,3.96,4.22]],
    [[2.62,3.51,3.77],[2.68,3.61,3.87],[2.76,3.65,3.91],[2.86,3.74,4],[2.98,3.89,4.15],[3.03,3.99,4.25],[3.14,4.13,4.39],[3.17,4.18,4.44]],
]
LARGE = [
    [[2.91,3.73,3.99],[3.13,3.95,4.21],[3.38,4.20,4.46],[3.78,4.60,4.86],[4.22,5.04,5.30],[4.60,5.42,5.68],[4.75,5.57,5.83],[5,5.82,6.08],[5.10,5.92,6.18],[5.28,6.10,6.36],[5.44,6.26,6.52],[5.85,6.67,6.93]],
    [[3.15,3.97,4.23],[3.39,4.21,4.47],[3.66,4.48,4.74],[4.07,4.89,5.15],[4.52,5.34,5.60],[4.91,5.73,5.99],[5.07,5.89,6.15],[5.33,6.15,6.41],[5.47,6.29,6.55],[5.67,6.49,6.75],[5.84,6.66,6.92],[6.26,7.08,7.34]],
]
NAMES = ['小号标准尺寸','大号标准尺寸','小号大件','大号大件','超大件0–50磅','超大件50–70磅','超大件70–150磅','超大件超过150磅']

def dec(x):
    v = D(str(x))
    if not v.is_finite():
        raise ValueError('数值必须有限')
    return v

def up(x, step='0.01'):
    step = dec(step)
    return (x / step).to_integral_value(rounding=ROUND_CEILING) * step

def fba(kg, dims, price, peak, fuel, special):
    short, middle, long = sorted(v / D('2.54') for v in dims)
    actual = kg / D('0.45359237')
    girth = long + 2 * (short + middle)
    small = long <= 15 and middle <= 12 and short <= D('.75') and actual <= 1
    dimensional = long * (middle if small else max(middle, D(2))) * (short if small else max(short, D(2))) / 139
    shipping = max(actual, dimensional)
    if small:
        tier = 0
    elif long <= 18 and middle <= 14 and short <= 8 and shipping <= 20:
        tier = 1
    elif long <= 37 and middle <= 28 and short <= 20 and girth <= 130 and shipping <= 50:
        tier = 2
    elif long <= 59 and middle <= 33 and short <= 33 and girth <= 130 and shipping <= 50:
        tier = 3
    else:
        tier = 4 if shipping <= 50 else 5 if shipping <= 70 else 6 if shipping <= 150 else 7
    band = 0 if price < 10 else 1 if price <= 50 else 2
    if tier == 0:
        charge = up(actual, '.125')
        base = dec(SMALL[peak][max(0, int(charge * 8)-1)][band])
    elif tier == 1:
        charge = up(shipping, '.25')
        if charge <= 3:
            base = dec(LARGE[peak][max(0, int(charge * 4)-1)][band])
        else:
            base = dec(([6.69,7.51,7.77] if peak else [6.15,6.97,7.23])[band]) + (charge-3)*4*D('.08')
    else:
        charge = up(actual if tier == 7 else shipping, '1')
        table = {2:[6.78,7.55,7.82,8.59],3:[8.58,9.35,9.62,10.39],4:[25.56,26.33,28.29,29.06],5:[36.55,37.32,39.36,40.13],6:[50.55,51.32,54.97,55.74],7:[194.18,194.95,202.69,203.46]}
        base = dec(table[tier][int(peak)*2 + int(band != 0)])
        start, rate = (1,'.38') if tier <= 4 else (51,'.75') if tier == 5 else (71,'.75') if tier == 6 else (151,'.19')
        base += max(D(0), charge-start)*dec(rate)
    needs_special = 4 <= tier <= 6 and (long > 96 or girth > 130)
    fuel_fee = base * D('.035') if fuel else D(0)
    total = None if needs_special and special is None else up(base + fuel_fee + (up(special) if needs_special else 0))
    return dict(tier=NAMES[tier],actual_lb=actual,dimensional_lb=dimensional,charge_lb=charge,base_usd=base,fuel_usd=fuel_fee,needs_special=needs_special,total_usd=total)

def calculate(data):
    assumptions = ['FBA为固定2026美国非服装参考费率，非实时；未覆盖仓储、关税、认证、开模等。']
    calculation_mode = data.get('mode', 'profit')
    ad_model = data.get('advertising_model', 'percent')
    if calculation_mode not in ('profit', 'cost_ceiling'):
        raise ValueError('mode必须为profit或cost_ceiling')
    if ad_model not in ('percent', 'bid_cvr'):
        raise ValueError('advertising_model必须为percent或bid_cvr')
    if ad_model == 'bid_cvr' and data.get('advertising_pct') is not None:
        raise ValueError('建议竞价测算与advertising_pct互斥，不能重复扣广告')
    if ad_model == 'percent' and any(data.get(k) is not None for k in ('suggested_bid_usd','conversion_rate_pct')):
        raise ValueError('百分比广告预算不能同时提供竞价/转化率输入')
    required = ['site','price_usd','quantity','fx','weight_kg','length_cm','width_cm','height_cm','season']
    required += ['unit_cost_cny'] if calculation_mode == 'profit' else ['target_margin_pct']
    if ad_model == 'bid_cvr':
        required += ['suggested_bid_usd', 'conversion_rate_pct']
    missing = [key for key in required if data.get(key) is None]
    if missing:
        return dict(status='needs_data',mode=calculation_mode,missing=missing,profit_usd=None,margin=None,assumptions=assumptions)
    if data['season'] not in ('off','peak'):
        raise ValueError('season必须为off或peak')
    if not isinstance(data.get('fuel', True), bool):
        raise ValueError('fuel必须为布尔值')
    n = dec(data['quantity'])
    if n < 1 or n != int(n):
        raise ValueError('quantity必须为正整数')
    p,fx,kg,l,w,h = [dec(data[k]) for k in ['price_usd','fx','weight_kg','length_cm','width_cm','height_cm']]
    c = dec(data['unit_cost_cny']) if calculation_mode == 'profit' else None
    if p < 0 or (c is not None and c < 0) or min(fx,kg,l,w,h) <= 0:
        raise ValueError('售价/成本不得负数；汇率/包装必须大于0')
    cb, pb = data.get('cost_basis','unit'), data.get('package_basis','set')
    if cb not in ('unit','set') or pb not in ('unit','set'):
        raise ValueError('成本和包装basis必须为unit或set')
    if pb == 'unit' and n > 1:
        kg,w = kg*n,w*n
        assumptions.append('多件装包装按单件重量与宽度乘装数，长高不变；需实包复核。')
    mode = data.get('transport','sea')
    if mode not in ('sea','air','express'):
        raise ValueError('未知运输方式')
    defaults = {'sea':(12,6000),'air':(55,5000),'express':(None,None)}
    rate, divisor = data.get('rate_cny_kg',defaults[mode][0]),data.get('divisor',defaults[mode][1])
    if rate is None or divisor is None:
        return dict(status='needs_data',mode=calculation_mode,missing=['rate_cny_kg/divisor'],profit_usd=None,margin=None,assumptions=assumptions)
    rate, divisor = dec(rate),dec(divisor)
    if rate < 0 or divisor <= 0:
        raise ValueError('运输单价>=0，体积除数>0')
    special = None if data.get('special_usd') is None else dec(data['special_usd'])
    if special is not None and special < 0:
        raise ValueError('特殊处理费不得为负')
    model = fba(kg,[l,w,h],p,data['season']=='peak',data.get('fuel',True),special) if data['site']=='US' and p>0 else None
    override = data.get('fba_override_usd')
    if override is not None and not data.get('fba_override_source'):
        raise ValueError('覆盖FBA需要来源')
    delivery = dec(override) if override is not None else model['total_usd'] if model else None
    if delivery is None:
        return dict(status='needs_data',mode=calculation_mode,missing=['special_usd或有来源的FBA' if model else '有来源的USD整套FBA'],fba_reference=model,profit_usd=None,margin=None,assumptions=assumptions)
    if delivery < 0:
        raise ValueError('FBA不得为负')
    if data['site'] != 'US' and data.get('usd_conversion_confirmed') is not True:
        raise ValueError('非US站点须确认售价和费用已换算USD')
    commission_rate = dec(data.get('commission_pct',15))/100
    return_rate = dec(data.get('returns_pct',5))/100
    ad_rate = dec(data.get('advertising_pct',20))/100 if ad_model == 'percent' else D(0)
    if any(v<0 or v>1 for v in (commission_rate,return_rate,ad_rate)):
        raise ValueError('费用百分比必须在0–100')
    fixed_ads = D(0)
    if ad_model == 'bid_cvr':
        bid, cvr = dec(data['suggested_bid_usd']), dec(data['conversion_rate_pct'])/100
        if bid < 0 or not 0 < cvr <= 1:
            raise ValueError('建议竞价>=0，假设转化率须在(0,100]')
        fixed_ads = bid/cvr
        assumptions.append('广告按建议竞价÷假设转化率测算，非实际CPC或实际广告成本。')
    else:
        assumptions.append('广告按售价百分比预算，非实际广告结果或归因ACoS。')
    commission,ads,returns = p*commission_rate,p*ad_rate+fixed_ads,p*return_rate
    volume = l*w*h/divisor
    bill = max(kg,volume)
    freight = up(bill*rate/fx)
    cost_set = (c*n if cb=='unit' else c) if c is not None else None
    procurement = cost_set/fx if cost_set is not None else None
    profit = p-procurement-freight-delivery-commission-ads-returns if procurement is not None else None
    contribution = profit+ads if profit is not None else None
    variable_rate = commission_rate+return_rate+ad_rate
    breakeven = (procurement+freight+delivery+fixed_ads)/(1-variable_rate) if procurement is not None and variable_rate<1 else None
    result = dict(status='ok' if calculation_mode=='profit' else 'ceiling_estimate',mode=calculation_mode,currency='USD',fee_version='2026-US-non-apparel-fixed',quantity=int(n),price_usd=p,cost_set_cny=cost_set,procurement_usd=procurement,volume_kg=volume,billable_kg=bill,freight_usd=freight,fba_usd=delivery,fba_reference=model,fba_source=data.get('fba_override_source','固定参考费率'),commission_usd=commission,advertising_model=ad_model,advertising_usd=ads,returns_usd=returns,profit_usd=profit,margin=profit/p if profit is not None and p else None,pre_ad_profit_usd=contribution,pre_ad_margin=contribution/p if contribution is not None and p else None,breakeven_price_fixed_fba_usd=breakeven,assumptions=assumptions)
    if calculation_mode == 'cost_ceiling':
        assumptions.append('仅为目标利润率下采购上限情景，尚无采购成本，不代表利润已验证。')
    if data.get('target_margin_pct') is not None:
        target = dec(data['target_margin_pct'])/100
        if not 0 <= target <= 1:
            raise ValueError('目标利润率必须在0–100')
        cap = (p*(1-variable_rate-target)-fixed_ads-freight-delivery)*fx
        result.update(target_margin=target,max_set_cost_cny=cap,max_unit_cost_cny=cap/n)
    return result

def serial(value):
    if isinstance(value,D):
        return float(value)
    raise TypeError(type(value).__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    result = calculate(json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=serial),encoding='utf-8')
    print(result['status'])
