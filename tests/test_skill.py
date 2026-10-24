"""Offline regression scenarios; no market requests or browser/account changes."""
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal as D
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from economics import calculate, serial
from render_report import render, sales_text, validate

FIXTURES = Path(__file__).parent/'fixtures'


def fixture(name):
    return json.loads((FIXTURES/(name+'.json')).read_text(encoding='utf-8'))


def base(**updates):
    data = fixture('mature_loss')['profit_input']
    data.update(price_usd=20, unit_cost_cny=10)
    data.update(updates)
    return data


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, default=serial), encoding='utf-8')


class EconomicsTests(unittest.TestCase):
    def test_percent_profit_arithmetic(self):
        result = calculate(base())
        self.assertEqual(result['status'], 'ok')
        expected = D(20)-D(10)/7-D(1)-D(4)-D(3)-D(4)-D(1)
        self.assertAlmostEqual(result['profit_usd'], expected, places=24)

    def test_cost_ceiling_without_zero_cost(self):
        data = base(mode='cost_ceiling', target_margin_pct=30)
        data.pop('unit_cost_cny')
        result = calculate(data)
        self.assertEqual(result['status'], 'ceiling_estimate')
        self.assertEqual(result['max_set_cost_cny'], 7)
        for key in ('profit_usd','margin','procurement_usd','cost_set_cny'):
            self.assertIsNone(result[key])

    def test_ceiling_inverse_in_both_ad_modes(self):
        for ad in ({}, {'advertising_model':'bid_cvr','suggested_bid_usd':0.2,'conversion_rate_pct':10}):
            with self.subTest(ad=ad):
                data = base(mode='cost_ceiling', target_margin_pct=25, **ad)
                data.pop('unit_cost_cny')
                result = calculate(data)
                data.update(mode='profit', cost_basis='set', unit_cost_cny=result['max_set_cost_cny'])
                self.assertAlmostEqual(calculate(data)['margin'], D('.25'), places=24)

    def test_ad_bid_and_conversion_are_scenario(self):
        result = calculate(base(advertising_model='bid_cvr', suggested_bid_usd=1, conversion_rate_pct=10))
        self.assertEqual(result['advertising_usd'], 10)
        self.assertTrue(any('非实际CPC' in x for x in result['assumptions']))
        self.assertNotIn('actual_cpc_usd', result)

    def test_mutually_exclusive_ad_inputs(self):
        for data in (base(advertising_model='bid_cvr', advertising_pct=20, suggested_bid_usd=1, conversion_rate_pct=10),
                     base(suggested_bid_usd=1), base(conversion_rate_pct=10)):
            with self.assertRaises(ValueError):
                calculate(data)

    def test_bad_or_missing_cvr(self):
        for cvr in (0,-1,101):
            with self.assertRaises(ValueError):
                calculate(base(advertising_model='bid_cvr', suggested_bid_usd=1, conversion_rate_pct=cvr))
        self.assertEqual(calculate(base(advertising_model='bid_cvr', suggested_bid_usd=1))['status'], 'needs_data')

    def test_pack_cost_not_double_counted(self):
        unit = calculate(base(quantity=2, unit_cost_cny=35))
        whole = calculate(base(quantity=2, unit_cost_cny=70, cost_basis='set'))
        self.assertEqual(unit['cost_set_cny'], 70)
        self.assertEqual(unit['profit_usd'], whole['profit_usd'])

    def test_missing_cost_does_not_mean_free(self):
        data = base()
        data.pop('unit_cost_cny')
        result = calculate(data)
        self.assertEqual(result['status'], 'needs_data')
        self.assertIsNone(result['profit_usd'])

    def test_unknown_package_blocks_both_modes(self):
        for mode in ('profit','cost_ceiling'):
            result = calculate(base(mode=mode, target_margin_pct=30, weight_kg=None))
            self.assertEqual(result['status'], 'needs_data')
            self.assertIsNone(result['profit_usd'])
            self.assertNotIn('max_set_cost_cny', result)

    def test_negative_cost_ceiling_is_retained(self):
        result = calculate(base(mode='cost_ceiling', target_margin_pct=30, price_usd=5))
        self.assertLess(result['max_set_cost_cny'], 0)

    def test_bid_breakeven_equation(self):
        data = base(advertising_model='bid_cvr', suggested_bid_usd=1, conversion_rate_pct=10)
        data['price_usd'] = calculate(data)['breakeven_price_fixed_fba_usd']
        self.assertAlmostEqual(calculate(data)['profit_usd'], D(0), places=24)

    def test_non_us_requires_conversion_confirmation(self):
        with self.assertRaises(ValueError):
            calculate(base(site='UK'))
        result = calculate(base(site='UK', usd_conversion_confirmed=True))
        self.assertIsNone(result['fba_reference'])

    def test_fee_override_is_not_double_deducted(self):
        a, b = calculate(base(fba_override_usd=4)), calculate(base(fba_override_usd=5))
        self.assertEqual(a['profit_usd']-b['profit_usd'], 1)


class ReportTests(unittest.TestCase):
    def run_fixture(self, name, target, include_html=False):
        case = fixture(name)
        if 'profit_input' in case:
            write(target/'profit-result.json', calculate(case['profit_input']))
        write(target/'research.json', case['research'])
        return render(target/'research.json', target, include_html)

    def test_four_scenarios_end_to_end(self):
        for name, decision in (('mature_loss','淘汰'),('new_consumable','可推进'),('parent_only','有机会推进'),('no_cost','可推进')):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)
                self.run_fixture(name, out)
                text = (out/'report.md').read_text(encoding='utf-8')
                self.assertIn(decision, text)
                self.assertFalse((out/'report.html').exists())
                if name == 'mature_loss':
                    self.assertLess(calculate(fixture(name)['profit_input'])['profit_usd'], 0)
                if name == 'no_cost':
                    self.assertFalse((out/'profit-result.json').exists())
                    self.assertIn('未计算利润', text)

    def test_parent_only_keeps_signal_and_public_limitation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.run_fixture('parent_only', out, True)
            page = (out/'report.html').read_text(encoding='utf-8')
            self.assertIn('本款待补；父体参考：235', page)
            self.assertIn('&lt;50', page)
            before_tabs = page.split('<nav')[0]
            self.assertIn('不能据父体估算决定本款备货', before_tabs)
            self.assertNotIn('暂无关键数据缺口', page)
            sales_panel = page.split('<h2>销量</h2>')[1].split('</section>')[0]
            self.assertNotIn('histogram-bar', sales_panel)

    def test_parent_series_rejected_as_target_sales(self):
        data = fixture('no_cost')['research']
        data['sales']['scope'] = 'parent'
        with self.assertRaises(ValueError):
            validate(data)

    def test_purchase_band_not_numeric_sales(self):
        with self.assertRaises(ValueError):
            sales_text({'monthly_sales': {'value':50,'kind':'purchase_band','scope':'child'}})

    def test_unknown_sales_and_integer_chart_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.run_fixture('no_cost', out, True)
            page = (out/'report.html').read_text(encoding='utf-8')
            self.assertIn('class="bar-value">82</text>', page)
            self.assertIn('class="bar-value">122</text>', page)
            self.assertIn('待补</text>', page)
            self.assertNotIn('悬停或聚焦', page)
            self.assertIn('https://www.amazon.com/dp/B000000001', page)

    def test_dashboard_default_and_excluded_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.run_fixture('new_consumable', out, True)
            page = (out/'report.html').read_text(encoding='utf-8')
            dash = page.split('<div id="dashboard"')[1].split('<div id="report"')[0]
            self.assertNotIn('四项快速验证', dash)
            self.assertNotIn('关键缺口与推进动作', dash)
            self.assertIn('aria-selected="true" aria-controls="dashboard"', page)
            self.assertNotIn('MCP', page)

    def test_only_sellersprite_market_sources(self):
        for kind in ('web','mcp','sif','user'):
            data = fixture('no_cost')['research']
            data['sources'][0]['kind'] = kind
            with self.assertRaises(ValueError):
                validate(data)
        data = fixture('no_cost')['research']
        data['sources'].append(dict(data['sources'][0], id='U01', kind='user', role='business_input'))
        validate(data)

    def test_unresolved_refs_and_false_no_data_rejected(self):
        data = fixture('no_cost')['research']
        data['key_evidence'][0]['source_ids'] = ['missing']
        with self.assertRaises(ValueError):
            validate(data)
        data = fixture('no_cost')['research']
        data['coverage'] = [{'field':'销量','status':'no_data','attempts':[]}]
        with self.assertRaises(ValueError):
            validate(data)

    def test_ceiling_report_never_claims_profit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            data = fixture('no_cost')['research']
            data['profit_file'] = 'profit-result.json'
            write(out/'profit-result.json', calculate(base(mode='cost_ceiling', target_margin_pct=30)))
            write(out/'research.json', data)
            render(out/'research.json', out, True)
            text = (out/'report.md').read_text(encoding='utf-8')
            self.assertIn('采购成本及利润仍未知', text)
            self.assertNotIn('计算结果：利润', text)

    def test_dependency_path_cannot_escape_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            data = fixture('no_cost')['research']
            data['profit_file'] = '../outside.json'
            write(out/'research.json', data)
            with self.assertRaises(ValueError):
                render(out/'research.json', out)

    def test_html_is_escaped_and_old_page_not_left_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            data = fixture('no_cost')['research']
            data['summary'] = '<script>alert(1)</script>'
            write(out/'research.json', data)
            render(out/'research.json', out, True)
            page = (out/'report.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>alert(1)</script>', page)
            with self.assertRaises(ValueError):
                render(out/'research.json', out)

    def test_cli_defaults_to_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write(out/'research.json', fixture('no_cost')['research'])
            result = subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/render_report.py'),'--input',str(out/'research.json'),'--out-dir',str(out)],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((out/'report.md').exists())
            self.assertFalse((out/'report.html').exists())

    def test_historical_variant_invariants(self):
        case = fixture('variant-regression')
        text = sales_text({'monthly_sales': {'value':case['parent_estimate'],'kind':'estimate','scope':'parent','period':'历史测试'}})
        self.assertIn('本款待补', text)
        self.assertEqual(case['target_purchase_band'], '<50')


if __name__ == '__main__':
    unittest.main(verbosity=2)
