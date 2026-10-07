import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/workflow/scripts'
sys.path.insert(0, str(SCRIPTS))
from crap import calculate

MEASURED = dict(file='src/a.ts', name='choose', line=1, complexity=4,
                covered=1, total=2, coverageKind='line')


class CrapTests(unittest.TestCase):
    def test_formula_and_unrounded_threshold(self):
        result = calculate({'functions': [MEASURED, {**MEASURED, 'name': 'uncovered', 'covered': 0}]}, 6)
        self.assertEqual([f['crap'] for f in result['functions']], [20, 6])
        self.assertEqual(result['findings'], 1)
        self.assertEqual(calculate({'functions': [{**MEASURED, 'covered': 2}]}, 4)['findings'], 0)
        self.assertEqual(calculate({'functions': [MEASURED]}, 5.99999)['findings'], 1)

    def test_invalid_measurements_and_thresholds(self):
        changes = [dict(complexity=-1), dict(complexity='4'), dict(covered=3), dict(covered=-1),
                   dict(total=0), dict(line=0), dict(coverageKind=None), dict(file=''),
                   dict(total=1.5), dict(covered=True), dict(complexity=2**53)]
        for functions in [[], [MEASURED, MEASURED], [None], *[[{**MEASURED, **c}] for c in changes]]:
            with self.subTest(functions=functions), self.assertRaises(ValueError):
                calculate({'functions': functions}, 6)
        for limit in [None, '30', -1, 0, float('nan'), float('inf'), True, 10**400]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                calculate({'functions': [MEASURED]}, limit)

    def test_cli_exit_codes_and_json_output(self):
        for limit, expected in [(6, 0), (5, 1), (None, 2)]:
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                report = json.dumps({'functions': [MEASURED]})
                code = f"from pathlib import Path; Path('report.json').write_text({report!r})"
                config = dict(cwd='.', command=[sys.executable, '-c', code], report='report.json', maxCrap=limit)
                path = root / 'config.json'
                path.write_text(json.dumps(config))
                result = subprocess.run([sys.executable, str(SCRIPTS / 'crap.py'), str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected != 2:
                    self.assertEqual(json.loads(result.stdout)['functions'][0]['crap'], 6)
