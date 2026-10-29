"""Call-only dismissal, including native event lifetime and physical coordinates."""
import ctypes
from ctypes import wintypes
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton,QWidget
from companion.ui import InteractionBubble,Resident,create_application
from companion.core import Notice
from companion.call_dismiss import NativeClickHook,MouseData

class CallDismissTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.bubble=InteractionBubble();self.guard=self.bubble.call_dismiss
        self.resident=Resident(100,character='A');self.resident.show();self.guard.resident=self.resident
        self.outside=QPushButton('outside');self.outside.show();self.app.processEvents()
    def tearDown(self):
        self.guard.close()
        for widget in (self.bubble,self.resident,self.outside):widget.hide();widget.deleteLater()
        self.app.processEvents()
    def open(self):self.bubble.open_choices();self.app.processEvents();self.assertTrue(self.bubble.isVisible())
    def test_external_qt_click_closes_call_and_is_delivered_to_its_target(self):
        clicked=Mock();self.outside.clicked.connect(clicked);self.open()
        QTest.mouseClick(self.outside,Qt.MouseButton.LeftButton)
        self.assertFalse(self.bubble.isVisible());clicked.assert_called_once();self.assertTrue(self.resident.isVisible())
        self.assertFalse(self.guard.installed);self.assertFalse(self.guard.native.handle)
    def test_choice_button_executes_without_premature_dismissal_and_background_closes(self):
        selected=[];self.bubble.selected.connect(selected.append);self.open()
        QTest.mouseClick(self.bubble.buttons['settings'],Qt.MouseButton.LeftButton)
        self.assertEqual(selected,['settings']);self.assertTrue(self.bubble.isVisible())
        QTest.mouseClick(self.bubble,Qt.MouseButton.LeftButton,pos=QPoint(3,3))
        self.assertFalse(self.bubble.isVisible())
    def test_character_left_click_only_dismisses_and_next_click_works(self):
        clicked=Mock();self.resident.clicked.connect(clicked);self.open()
        QTest.mouseClick(self.resident,Qt.MouseButton.LeftButton,pos=QPoint(40,40))
        self.assertFalse(self.bubble.isVisible());clicked.assert_not_called();self.assertFalse(self.guard.installed)
        QTest.mouseClick(self.resident,Qt.MouseButton.LeftButton,pos=QPoint(40,40));clicked.assert_called_once()
    def test_second_character_right_click_remains_a_single_toggle(self):
        def toggle(_):
            if self.bubble.isVisible():self.bubble.hide()
            else:self.bubble.open_choices()
        self.resident.context_requested.connect(toggle);self.open()
        QTest.mouseClick(self.resident,Qt.MouseButton.RightButton,pos=QPoint(40,40))
        self.assertFalse(self.bubble.isVisible());self.assertFalse(self.guard.native.handle)
    def test_native_external_click_and_stale_events_cannot_dismiss_new_content(self):
        self.open();generation=self.guard.native.generation
        with patch.object(self.guard.native,'client_point',return_value=None):self.guard.native_press(500,600,0x0201,generation)
        self.assertFalse(self.bubble.isVisible());self.assertFalse(self.guard.native.handle)
        self.bubble.show_one_shot_form();self.bubble.reminder_message.setPlainText('keep')
        self.guard.native_press(500,600,0x0201,generation);QTest.mouseClick(self.outside,Qt.MouseButton.LeftButton)
        self.assertTrue(self.bubble.isVisible());self.assertEqual(self.bubble.reminder_message.toPlainText(),'keep')
        self.open();self.guard.native_press(500,600,0x0201,generation);self.assertTrue(self.bubble.isVisible())
    def test_native_button_hit_is_kept_and_other_view_does_not_enable_global_dismissal(self):
        self.open();button=self.bubble.buttons['calendar'];point=button.mapTo(self.bubble,button.rect().center())
        with patch.object(self.guard.native,'client_point',side_effect=lambda widget,x,y:point if widget is self.bubble else None):
            self.guard.native_press(100,100,0x0201,self.guard.native.generation)
        self.assertTrue(self.bubble.isVisible())
        self.bubble.display(Notice('','notification',True,kind='notification'))
        self.assertFalse(self.guard.installed);self.assertFalse(self.guard.native.handle)
        QTest.mouseClick(self.outside,Qt.MouseButton.LeftButton);self.assertTrue(self.bubble.isVisible())
    def test_native_registration_and_callback_always_forward_the_mouse_event(self):
        hook=NativeClickHook();received=[];hook.pressed.connect(lambda *args:received.append(args))
        self.assertTrue(hook.start())
        try:
            data=MouseData();data.pt.x=-500;data.pt.y=300
            with patch.object(hook.user,'CallNextHookEx',return_value=17) as forwarded:
                result=hook.dispatch(0,0x0201,ctypes.addressof(data));self.assertEqual(result,17)
                forwarded.assert_called_once();self.assertEqual(received,[(-500,300,0x0201,hook.generation)])
                hook.dispatch(-1,0x0201,ctypes.addressof(data));self.assertEqual(len(received),1)
        finally:hook.stop()
        self.assertFalse(hook.handle)
    def test_physical_client_coordinates_scale_and_foreign_windows_are_not_button_hits(self):
        hook=NativeClickHook();widget=SimpleNamespace(isVisible=lambda:True,winId=lambda:123,width=lambda:322,height=lambda:200)
        user=Mock();user.WindowFromPoint.return_value=124;user.GetAncestor.return_value=123
        def rect(_,pointer):
            value=ctypes.cast(pointer,ctypes.POINTER(wintypes.RECT)).contents;value.right=644;value.bottom=400;return True
        def local(_,pointer):
            value=ctypes.cast(pointer,ctypes.POINTER(wintypes.POINT)).contents;value.x=300;value.y=60;return True
        user.GetClientRect.side_effect=rect;user.ScreenToClient.side_effect=local
        with patch.object(hook,'user',user):
            self.assertEqual(hook.client_point(widget,-100,600),QPoint(150,30))
            user.GetAncestor.return_value=999;self.assertIsNone(hook.client_point(widget,-100,600))
