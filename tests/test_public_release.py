import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from render_report import render, validate


class PublicReleaseTests(unittest.TestCase):
    def data(self):
        return json.loads((ROOT/'tests/fixtures/standard-research.json').read_text(encoding='utf-8'))

    def test_mcp_is_attributed_and_business_inputs_stay_separate(self):
        d = self.data()
        d['sources'][0].update(kind='mcp', provider='Synthetic provider', tool='Synthetic query')
        validate(d)
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            (p/'research.json').write_text(json.dumps(d), encoding='utf-8')
            render(p/'research.json', p)
            html = (p/'report.html').read_text(encoding='utf-8')
            self.assertIn('Synthetic provider / Synthetic query', html)
            manifest = json.loads((p/'manifest.json').read_text(encoding='utf-8'))
            for f in manifest['files']:
                self.assertFalse(Path(f['path']).is_absolute())
                self.assertNotIn(str(p), f['path'])
        for missing in ('provider', 'tool'):
            value = d['sources'][0].pop(missing)
            with self.assertRaises(ValueError):
                validate(d)
            d['sources'][0][missing] = value
        d['sources'][0].update(kind='user', role='business_input')
        with self.assertRaises(ValueError):
            validate(d)

    def test_demo_and_image_are_traceable(self):
        d = json.loads((ROOT/'examples/demo/research.json').read_text(encoding='utf-8'))
        self.assertTrue(d['demo'])
        with tempfile.TemporaryDirectory() as temp:
            render(ROOT/'examples/demo/research.json', Path(temp))
            html = (Path(temp)/'report.html').read_text(encoding='utf-8')
            self.assertIn('data:image/png;base64,', html)
            self.assertIn('演示数据', html)
            self.assertIn('Kuma Product Research', html)


if __name__ == '__main__':
    unittest.main()
