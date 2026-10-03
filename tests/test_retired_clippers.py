import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetiredClippersTests(unittest.TestCase):
    def test_doctor_does_not_recommend_retired_applications(self):
        spec = importlib.util.spec_from_file_location('clip_library', ROOT / 'scripts/clip_library.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.doctor(ROOT)
        self.assertNotIn('supoclip_url', report)
        self.assertNotIn('supoclip_python', report['tools'])
        self.assertFalse(any('supoclip' in message.lower() or 'autoclip' in message.lower()
                             for message in report['automatic_clipping_blockers']))


if __name__ == '__main__':
    unittest.main()
