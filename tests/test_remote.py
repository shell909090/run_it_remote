import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from remote import local
from sync import api
from sync import sync
import rmtfunc

class RemoteTests(unittest.TestCase):
    def connect(self, protocol=local.BinaryEncoding):
        channel = type('Channel', (local.LocalChannel, protocol), {})()
        remote = local.Remote(channel)
        self.addCleanup(remote.close)
        return remote

    def test_protocols(self):
        for protocol in (local.BinaryEncoding, local.Base64Encoding):
            with self.subTest(protocol=protocol):
                remote = self.connect(protocol)
                self.assertEqual(remote.eval("('中文', bytes(range(256)), 42)"), ('中文', bytes(range(256)), 42))
                remote.execute('answer = 42')
                self.assertEqual(remote.eval('answer'), 42)

    def test_import_and_callback(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            remote = self.connect()
            self.assertEqual(remote.apply(rmtfunc.get_hostname), rmtfunc.get_hostname())
            remote.apply(rmtfunc.get_hostname_cb)
            remote.execute("print('中文输出')")
            remote.close()
        self.assertIn('中文输出', output.getvalue())
        self.assertIn('hostname:', output.getvalue())

    def test_sync(self):
        remote = self.connect()
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source'
            source.mkdir()
            (source / '中文.txt').write_bytes(b'\x00\xffhello')
            target = Path(tmp) / 'target'
            sync.sync_to(remote, str(target), str(source))
            self.assertEqual((target / '中文.txt').read_bytes(), b'\x00\xffhello')
            dest = Path(tmp) / 'back'
            info = sync.sync_back(remote, str(target), str(dest))
            self.assertEqual((dest / '中文.txt').read_bytes(), b'\x00\xffhello')
            doc = api.filist_load(api.filist_dump(info))
            self.assertIn('common', doc)

    def test_group(self):
        import os
        self.assertEqual(api.get_groupid(api.get_groupname(os.getgid())), os.getgid())

    def test_aes(self):
        remote = self.connect()
        remote.enable_aes()
        self.assertEqual(remote.eval("'hello' * 123"), 'hello' * 123)
