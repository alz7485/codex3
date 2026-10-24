from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace,ModuleType
import unittest
from unittest.mock import Mock,patch
from companion.outlook import show_calendar
from companion.dialogue import defaults,read_document


class OutlookNavigationTests(unittest.TestCase):
    def navigate(self,running=True,existing_window=True,fail=False):
        com=ModuleType('pythoncom');com.CoInitialize=Mock();com.CoUninitialize=Mock()
        explorer=SimpleNamespace(Display=Mock(),Activate=Mock())
        folder=SimpleNamespace(GetExplorer=Mock(return_value=explorer))
        namespace=SimpleNamespace(GetDefaultFolder=Mock(return_value=folder))
        app=SimpleNamespace(GetNamespace=Mock(side_effect=RuntimeError('blocked')) if fail else Mock(return_value=namespace),ActiveExplorer=lambda:explorer if existing_window else None)
        client=ModuleType('win32com.client');package=ModuleType('win32com');package.client=client
        client.GetActiveObject=Mock(return_value=app) if running else Mock(side_effect=RuntimeError('not running'))
        client.Dispatch=Mock(return_value=app)
        try:
            with patch.dict(sys.modules,{'pythoncom':com,'win32com':package,'win32com.client':client}),patch('companion.outlook.sys.platform','win32'):
                if fail:
                    with self.assertRaises(RuntimeError):show_calendar()
                else:show_calendar()
        finally:com.CoUninitialize.assert_called_once()
        com.CoInitialize.assert_called_once()
        return explorer,folder,namespace,client

    def test_explicit_calendar_navigation_reuses_running_window_without_item_writes(self):
        explorer,folder,namespace,client=self.navigate()
        self.assertIs(explorer.CurrentFolder,folder)
        namespace.GetDefaultFolder.assert_called_once_with(9)
        explorer.Display.assert_called_once();explorer.Activate.assert_called_once();client.Dispatch.assert_not_called()

    def test_explicit_navigation_can_start_outlook_and_create_explorer(self):
        explorer,folder,_namespace,client=self.navigate(running=False,existing_window=False)
        client.Dispatch.assert_called_once_with('Outlook.Application');folder.GetExplorer.assert_called_once()
        explorer.Activate.assert_called_once()

    def test_navigation_failure_always_releases_com(self):self.navigate(fail=True)

    def test_history_intro_upgrade_replaces_only_stock_wording(self):
        document=defaults();document.pop('conversation_flow_version')
        document['phrases']['控えめな皮肉屋']['activity_open']=['履歴を開きました。\\n日付を選んで、振り返ってみましょう。']
        document['phrases']['冷静な案内役']['activity_open']=['私が編集した案内です。']
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'dialogue.json';path.write_text(json.dumps(document));before=path.read_bytes()
            result=read_document(path)
            self.assertIn('今日',result['phrases']['控えめな皮肉屋']['activity_open'][0])
            self.assertEqual(result['phrases']['冷静な案内役']['activity_open'],['私が編集した案内です。'])
            self.assertEqual(path.read_bytes(),before)
