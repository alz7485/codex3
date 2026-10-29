"""Transient outside-click dismissal for the call menu; no input is recorded."""
import ctypes
from ctypes import wintypes
import sys

from PySide6.QtCore import QEvent,QObject,QPoint,Qt,QTimer,Signal
from PySide6.QtWidgets import QApplication,QAbstractButton,QWidget

# Keep a C callback alive until Windows confirms that its hook is removed.
_INSTALLED=[]
_DOWN={0x0201,0x0204,0x0207,0x020B}


class MouseData(ctypes.Structure):
    _fields_=[('pt',wintypes.POINT),('mouseData',wintypes.DWORD),('flags',wintypes.DWORD),
              ('time',wintypes.DWORD),('extra',ctypes.c_size_t)]


class NativeClickHook(QObject):
    pressed=Signal(int,int,int,int)
    def __init__(self,parent=None):
        super().__init__(parent);self.handle=None;self.generation=0;self.user=None;self.callback=None
        if sys.platform!='win32':return
        self.user=ctypes.WinDLL('user32',use_last_error=True);self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        proc=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM)
        self.user.SetWindowsHookExW.argtypes=[ctypes.c_int,proc,wintypes.HINSTANCE,wintypes.DWORD];self.user.SetWindowsHookExW.restype=wintypes.HANDLE
        self.user.UnhookWindowsHookEx.argtypes=[wintypes.HANDLE];self.user.UnhookWindowsHookEx.restype=wintypes.BOOL
        self.user.CallNextHookEx.argtypes=[wintypes.HANDLE,ctypes.c_int,wintypes.WPARAM,wintypes.LPARAM];self.user.CallNextHookEx.restype=ctypes.c_ssize_t
        self.kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];self.kernel.GetModuleHandleW.restype=wintypes.HMODULE
        self.user.WindowFromPoint.argtypes=[wintypes.POINT];self.user.WindowFromPoint.restype=wintypes.HWND
        self.user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT];self.user.GetAncestor.restype=wintypes.HWND
        self.user.ScreenToClient.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.POINT)];self.user.ScreenToClient.restype=wintypes.BOOL
        self.user.GetClientRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];self.user.GetClientRect.restype=wintypes.BOOL
        self.callback=proc(self.dispatch)
    def dispatch(self,code,message,address):
        try:
            if code>=0 and message in _DOWN and self.handle:
                data=ctypes.cast(address,ctypes.POINTER(MouseData)).contents
                self.pressed.emit(data.pt.x,data.pt.y,message,self.generation)
        except Exception:pass  # Never interrupt the system's mouse-event chain.
        return self.user.CallNextHookEx(None,code,message,address)
    def start(self):
        if self.handle:return True
        self.generation+=1
        if self.user is None:return False
        self.handle=self.user.SetWindowsHookExW(14,self.callback,self.kernel.GetModuleHandleW(None),0)
        if self.handle:_INSTALLED.append(self)
        return bool(self.handle)
    def stop(self):
        self.generation+=1
        if self.handle and self.user.UnhookWindowsHookEx(self.handle):
            self.handle=None
            if self in _INSTALLED:_INSTALLED.remove(self)
    def client_point(self,widget,x,y):
        """Map physical Windows coordinates to this window's logical pixels.

        Checking the window under the pointer avoids accepting a button hidden
        behind another application, including mixed-DPI monitor layouts.
        """
        if self.user is None or widget is None or not widget.isVisible():return None
        hwnd=int(widget.winId());point=wintypes.POINT(x,y)
        hit=self.user.WindowFromPoint(point)
        if not hit or self.user.GetAncestor(hit,2)!=hwnd:return None
        rect=wintypes.RECT()
        if not self.user.GetClientRect(hwnd,ctypes.byref(rect)) or not rect.right or not rect.bottom:return None
        if not self.user.ScreenToClient(hwnd,ctypes.byref(point)):return None
        return QPoint(round(point.x*widget.width()/rect.right),round(point.y*widget.height()/rect.bottom))


class CallDismissGuard(QObject):
    def __init__(self,bubble):
        super().__init__(bubble);self.bubble=bubble;self.resident=None;self.closed=False;self.installed=False
        self.native=NativeClickHook(self);self.native.pressed.connect(self.native_press,Qt.ConnectionType.QueuedConnection)
        self.suppress_character=False;self.release_timer=QTimer(self);self.release_timer.setSingleShot(True)
        self.release_timer.setInterval(500);self.release_timer.timeout.connect(self.clear_suppression)
        bubble.hidden.connect(self.stop);bubble.content_changing.connect(self.stop)
        bubble.destroyed.connect(self.native.stop);bubble.installEventFilter(self)
    def enabled(self):
        b=self.bubble
        return not self.closed and b.isVisible() and b.current is None and b.choice_row.isVisible()
    def start(self):
        self.clear_suppression()
        if not self.enabled():return
        if not self.installed:QApplication.instance().installEventFilter(self);self.installed=True
        self.native.start()
    def stop(self):
        self.native.stop()
        if not self.suppress_character and self.installed:
            QApplication.instance().removeEventFilter(self);self.installed=False
    def close(self):
        if self.closed:return
        self.closed=True;self.clear_suppression();self.stop()
    def clear_suppression(self):
        self.release_timer.stop();self.suppress_character=False
        if not self.enabled():self.stop()
    def suppress_once(self):
        self.suppress_character=True;self.release_timer.start()
    def is_button(self,widget):
        child=widget;button=None
        while isinstance(child,QWidget) and child is not self.bubble:
            if isinstance(child,QAbstractButton):button=child
            child=child.parentWidget()
        return button if child is self.bubble else None
    def native_press(self,x,y,message,generation):
        if generation!=self.native.generation or not self.enabled():return
        point=self.native.client_point(self.bubble,x,y)
        if point is not None and self.is_button(self.bubble.childAt(point)):return
        resident=self.native.client_point(self.resident,x,y)
        # A second right click on the character uses the existing toggle.
        if message==0x0204 and (point is not None or resident is not None):return
        if message==0x0201 and resident is not None:self.suppress_once()
        self.bubble.dismiss()
    def eventFilter(self,watched,event):
        kind=event.type()
        if (self.suppress_character and watched is self.resident and kind in (QEvent.Type.MouseButtonPress,QEvent.Type.MouseButtonRelease)
                and event.button()==Qt.MouseButton.LeftButton):
            if kind==QEvent.Type.MouseButtonRelease:self.clear_suppression()
            return True
        if kind==QEvent.Type.WindowDeactivate and watched is self.bubble and self.enabled() and not self.native.handle:
            self.bubble.dismiss();return False
        if kind not in (QEvent.Type.MouseButtonPress,QEvent.Type.NonClientAreaMouseButtonPress) or not self.enabled() or not isinstance(watched,QWidget):return False
        button=self.is_button(watched)
        if button is not None and button.rect().contains(button.mapFromGlobal(event.globalPosition().toPoint())):return False
        inside=watched is self.bubble or self.bubble.isAncestorOf(watched)
        if event.button()==Qt.MouseButton.RightButton and (inside or watched is self.resident):return False
        if watched is self.resident and event.button()==Qt.MouseButton.LeftButton:self.suppress_once()
        self.bubble.dismiss()
        return inside or watched is self.resident
