"""A timeout must stop the CLI's child from changing the scored fixture later."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from git_safety_eval.agents import _run
from git_safety_eval.sandbox import Sandbox


@unittest.skipUnless(os.name == 'posix', 'process-group cleanup uses POSIX signals')
class ProcessCleanup(unittest.TestCase):
    def test_timeout_kills_child_before_late_mutation(self):
        with tempfile.TemporaryDirectory(prefix='git-safety-process-', dir='/var/tmp') as tmp:
            sb = Sandbox(Path(tmp) / 'case')
            sb.work.mkdir()
            marker = sb.work / 'late-write'
            child = f"import time; from pathlib import Path; time.sleep(0.8); Path({str(marker)!r}).write_text('late')"
            parent = f"import subprocess,time,sys; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)"
            with patch('git_safety_eval.agents.shutil.which', return_value=None):
                error = _run([sys.executable, '-c', parent], sb, sb.env, 0.2)
            self.assertIn('timed out', error)
            time.sleep(1)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
