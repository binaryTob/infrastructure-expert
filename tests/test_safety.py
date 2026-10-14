"""Offline regressions: synthetic evidence and fake SSH, never a remote target."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RedactionTests(unittest.TestCase):
    def test_json_env_bearer_and_private_key_values_are_removed(self):
        raw = ('{"password": "fixture-only-value", "api_key": "fixture-key"}\n'
               'DB_PASSWORD=fixture-db\nAuthorization: Bearer fixture-bearer\n'
               '-----BEGIN PRIVATE KEY-----\nfixture-material\n-----END PRIVATE KEY-----')
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts/redact.py')],
            input=raw, text=True, capture_output=True, check=True,
        )
        for value in ('fixture-only-value', 'fixture-key', 'fixture-db',
                      'fixture-bearer', 'fixture-material'):
            self.assertNotIn(value, result.stdout)
        self.assertIn('password', result.stdout)

    def test_capture_fails_closed_when_redactor_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            out, err = Path(directory) / 'out', Path(directory) / 'err'
            result = subprocess.run([
                sys.executable, str(ROOT / 'scripts/capture_redacted.py'),
                str(out), str(err), '/bin/false', sys.executable, '-c',
                'print("fixture-only-value")',
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())
            self.assertFalse(err.exists())
            self.assertNotIn('fixture-only-value', result.stderr)


class SshWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'scripts', self.root / 'scripts')
        (self.root / 'config').mkdir()
        self.config = {'ssh': {
            'host': '192.0.2.10', 'user': 'operator', 'port': 2222,
            'private_key': '~/.ssh/fixture-key',
            'connect_timeout': 7, 'command_timeout': 9,
        }}
        (self.root / 'config/target.json').write_text(json.dumps(self.config))
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        ssh = self.bin / 'ssh'
        ssh.write_text('#!' + sys.executable + '\n'
                       'import json, os, pathlib, sys\n'
                       'pathlib.Path(os.environ["FAKE_SSH_ARGS"]).write_text(json.dumps(sys.argv[1:]))\n'
                       'print("password=fixture-output")\n')
        ssh.chmod(0o700)
        self.args_path = self.root / 'ssh-args.json'
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('SSH_') and key not in (
                        'CONNECT_TIMEOUT', 'COMMAND_TIMEOUT', 'EVIDENCE_RUN_ID')}
        self.env.update(PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        FAKE_SSH_ARGS=str(self.args_path))

    def run_wrapper(self, command='uname -a', basename='fixture', level='L1', **env):
        return subprocess.run([
            'bash', str(self.root / 'scripts/ssh_exec.sh'), basename, 'system',
            level, command, str(self.root / 'evidence'),
        ], env=self.env | env, capture_output=True, text=True, cwd=self.root)

    def test_config_key_timeouts_port_and_environment_precedence(self):
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.args_path.read_text())
        self.assertIn(str(Path.home() / '.ssh/fixture-key'), args)
        self.assertIn('ConnectTimeout=7', args)
        self.assertIn('2222', args)
        self.assertEqual(args[-3:], ['--', 'operator@192.0.2.10', 'uname -a'])
        result = self.run_wrapper(SSH_PORT='2200', CONNECT_TIMEOUT='5')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(self.args_path.read_text())
        self.assertIn('2200', args)
        self.assertIn('ConnectTimeout=5', args)

    def test_missing_target_invalid_metadata_and_l3_never_reach_ssh(self):
        for params in ({'basename': '../escape'}, {'level': 'L3'},
                       {'command': 'systemctl restart sshd'}):
            with self.subTest(params=params):
                self.assertNotEqual(self.run_wrapper(**params).returncode, 0)
                self.assertFalse(self.args_path.exists())
        (self.root / 'config/target.json').unlink()
        result = self.run_wrapper()
        self.assertEqual(result.returncode, 4)
        self.assertNotIn('command not found', result.stderr)

    def test_command_and_streams_redacted_and_evidence_private(self):
        result = self.run_wrapper(command='printf password=fixture-command')
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = self.root / 'evidence/fixture.yml'
        record = yaml.safe_load(evidence.read_text())
        for value in ('fixture-command', 'fixture-output'):
            self.assertNotIn(value, evidence.read_text())
            self.assertNotIn(value, result.stdout + result.stderr)
        self.assertIn('REDACTED', record['command'])
        self.assertIn('REDACTED', record['stdout'])
        self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)


class ReportTests(unittest.TestCase):
    def test_untrusted_metadata_is_escaped_and_execution_is_not_invented(self):
        spec = importlib.util.spec_from_file_location('report', ROOT / 'scripts/gen_report.py')
        report = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(report)
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / '<fixture>'
            run.mkdir()
            inventory = {'host': {'ssh': {'host': '<img src=x onerror=alert(1)>'}}}
            html = report.gen_html(str(run), inventory=inventory)
            self.assertNotIn('<img src=x', html)
            self.assertIn('&lt;img', html)
            self.assertIn('no registrado', html)
            self.assertNotIn('Skills ejecutados: system-inventory', html)
            (run / 'skills-used.yaml').write_text(yaml.safe_dump({'skills': [
                {'id': '<completed>', 'status': 'executed'},
                {'id': 'never-ran', 'status': 'pending'},
            ]}))
            html = report.gen_html(str(run), inventory=inventory)
            self.assertIn('Skills ejecutados: &lt;completed&gt;', html)
            self.assertNotIn('never-ran', html)


if __name__ == '__main__':
    unittest.main()
