import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from render_report import validate,render,link_asins,esc
from research_sections import keyword_lines

def data(): return json.loads((ROOT/'tests/fixtures/standard-research.json').read_text(encoding='utf-8'))

class ResearchTests(unittest.TestCase):
    def test_heading_asin_stays_plain_and_numbers_grouped(self):
        html=link_asins('<h1>B000000001</h1><h3>B000000001 档位</h3><td>B000000001</td>','US')
        self.assertIn('<h1>B000000001</h1>',html)
        self.assertIn('<h3>B000000001 档位</h3>',html)
        self.assertEqual(html.count('href='),1)
        self.assertEqual(esc(21590),'21,590')
        self.assertEqual(esc('2026-09'),'2026-09')

    def test_combined_keyword_tooltip_preserves_gaps(self):
        html=keyword_lines(data(),esc)
        self.assertEqual(html.count('class="keyword-lines"'),1)
        self.assertIn('demo filter handheld',html)
        self.assertIn('1,234',html)
        self.assertIn('&quot;value&quot;: null',html)
        # Both histories break at August: single-point segments on each side.
        self.assertEqual(html.count('<polyline'),4)
        self.assertNotIn('histogram-bar',html)

    def test_standard_default_continuous_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); d=data(); (p/'research.json').write_text(json.dumps(d),encoding='utf-8')
            render(p/'research.json',p)
            html=(p/'report.html').read_text(encoding='utf-8')
            self.assertNotIn('role="tablist"',html)
            order=[html.index('<h2>'+s) for s in ('销量历史与销售对比','关键词需求与搜索趋势','竞争格局与价格带','差评主题与差异化机会','利润与压力情景')]
            self.assertEqual(order,sorted(order))
            for s in ('1,234','未获取到</text>','3/10','Synthetic quote','B000000002'): self.assertIn(s,html)
            self.assertNotIn('<script src=',html)
            self.assertIn('demo filter handheld',(p/'report.md').read_text(encoding='utf-8'))

    def test_grouped_reviews_and_legacy_decision_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=data()
            theme=copy.deepcopy(d['review_themes'][0]);theme.update(id='extra-theme',theme='Another pain point',count=2,sample_size=7)
            d['review_themes'].append(theme)
            for old,new in [('继续验证','可推进'),('待补证据','有机会推进'),('淘汰','淘汰')]:
                d['decision']=old
                (p/'research.json').write_text(json.dumps(d),encoding='utf-8');render(p/'research.json',p)
                page=(p/'report.html').read_text(encoding='utf-8')
                self.assertIn('>'+new+'</span>',page)
                self.assertEqual(page.count('class="review-card"'),len({t['asin'] for t in d['review_themes']}))
                self.assertIn('2/7',page);self.assertIn('3/10',page)
                self.assertIn('Another pain point',page)
                if old=='淘汰':self.assertIn('class="verdict verdict-reject"',page)

    def test_brief_default_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); d=data();d['mode']='brief'
            (p/'research.json').write_text(json.dumps(d),encoding='utf-8');render(p/'research.json',p)
            self.assertFalse((p/'report.html').exists())

    def test_missing_core_module_cannot_complete(self):
        for status in ('not_queried','blocked','partial','no_data'):
            d=data();d['module_status']['reviews'].update(status=status,reason='测试阻塞')
            with self.assertRaises(ValueError): validate(d)
        d['research_status']='partial';validate(d)

    def test_partial_requires_actual_attempt(self):
        d=data();d['research_status']='partial';d['module_status']['sales'].update(status='partial',attempts=[],reason='尚未查')
        with self.assertRaises(ValueError):validate(d)

    def test_parent_reference_and_band_boundaries(self):
        d=data();s=d['sales_series'][0];s['scope']='parent'
        with self.assertRaises(ValueError):validate(d)
        s['reference_only']=True;validate(d)
        s['kind']='purchase_band'
        with self.assertRaises(ValueError):validate(d)

    def test_no_fake_counts_or_quotes(self):
        for count,size in ((11,10),(1,0),(1,None),(2.5,10)):
            d=data();d['review_themes'][0].update(count=count,sample_size=size)
            with self.assertRaises(ValueError):validate(d)
        d=data();d['review_themes'][0]['quotes'][0].pop('review_id')
        with self.assertRaises(ValueError):validate(d)

    def test_series_unknown_negative_or_duplicate_rejected(self):
        for update in ({'subject':'missing'},{'scope':'unknown'}):
            d=data();d['sales_series'][0].update(update)
            with self.assertRaises(ValueError):validate(d)
        for val in (-1,float('nan'),'100+'):
            d=data();d['keyword_series'][0]['points'][0]['value']=val
            with self.assertRaises(ValueError):validate(d)
        d=data();d['sales_series'][0]['points'].append(d['sales_series'][0]['points'][0])
        with self.assertRaises(ValueError):validate(d)

    def test_no_business_input_as_market_data(self):
        d=data();d['sources'][0].update(kind='user',role='business_input')
        with self.assertRaises(ValueError):validate(d)

    def test_escaping_reviews_and_no_invented_evidence(self):
        d=data();d['opportunities'][0]['theme_ids']=['unknown']
        with self.assertRaises(ValueError):validate(d)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=data();d['review_themes'][0]['quotes'][0]['text']='<script>evil()</script>'
            (p/'research.json').write_text(json.dumps(d),encoding='utf-8');render(p/'research.json',p)
            html=(p/'report.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>evil()',html);self.assertIn('&lt;script&gt;evil()',html)

if __name__=='__main__':unittest.main(verbosity=2)
