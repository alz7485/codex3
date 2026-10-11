import sys,threading,unittest
sys.path.insert(0,'/workspace/attendsync-trial47/AttendSync')
from test_trial47_folder_drop import FolderDrop47,main
from PySide6.QtCore import QUrl,QPoint,QPointF,Qt,QMimeData,QThread
from PySide6.QtGui import QDragEnterEvent,QDragMoveEvent,QDropEvent
from PySide6.QtWidgets import QWidget,QLineEdit

class Audit47(FolderDrop47):
    def audit_every_widget(self):
        widgets=[self.w]+[w for w in self.w.findChildren(QWidget) if w.window() is self.w]
        for widget in widgets:
            with self.subTest(widget=type(widget).__name__,name=widget.objectName()):
                self.w.path.setText('before')
                events=self.dispatch(widget,self.mime([QUrl.fromLocalFile(str(self.folder))]))
                self.assertTrue(all(e.isAccepted() for e in events));self.assertEqual(self.w.path.text(),str(self.folder.resolve()))
        print('Audited native event targets:',len(widgets))
    def audit_polished_reparented_widget(self):
        other=QWidget();edit=QLineEdit(other);other.show();self.app.processEvents()
        try:
            edit.setParent(self.w.centralWidget());edit.show();self.app.processEvents()
            self.w.path.setText('before')
            events=self.dispatch(edit,self.mime([QUrl.fromLocalFile(str(self.folder))]))
            self.assertTrue(all(e.isAccepted() for e in events));self.assertEqual(self.w.path.text(),str(self.folder.resolve()));self.assertEqual(edit.text(),'')
        finally:other.close();other.deleteLater()
    def audit_copy_and_move_actions(self):
        mime=self.mime([QUrl.fromLocalFile(str(self.folder))])
        for actions in [Qt.MoveAction,Qt.LinkAction,Qt.CopyAction,Qt.CopyAction|Qt.MoveAction]:
            self.w.path.setText('before')
            events=[QDragEnterEvent(QPoint(5,5),actions,mime,Qt.LeftButton,Qt.NoModifier),QDropEvent(QPointF(5,5),actions,mime,Qt.LeftButton,Qt.NoModifier)]
            for e in events:self.app.sendEvent(self.w,e)
            expected=bool(actions & Qt.CopyAction)
            self.assertEqual(all(e.isAccepted() for e in events),expected)
            self.assertEqual(self.w.path.text(),str(self.folder.resolve()) if expected else 'before')
            self.assertTrue(self.folder.is_dir())
    def audit_deleted_between_enter_and_drop(self):
        mime=self.mime([QUrl.fromLocalFile(str(self.folder))]);self.w.path.setText('before')
        enter=QDragEnterEvent(QPoint(5,5),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
        self.app.sendEvent(self.w,enter);self.assertTrue(enter.isAccepted());self.folder.rmdir()
        drop=QDropEvent(QPointF(5,5),Qt.CopyAction,mime,Qt.LeftButton,Qt.NoModifier)
        self.app.sendEvent(self.w,drop);self.assertFalse(drop.isAccepted());self.assertEqual(self.w.path.text(),'before')
    def audit_disabled_path(self):
        self.w.path.setText('before');self.w.path.setEnabled(False)
        events=self.dispatch(self.w,self.mime([QUrl.fromLocalFile(str(self.folder))]))
        self.assertFalse(any(e.isAccepted() for e in events));self.assertEqual(self.w.path.text(),'before')
    def audit_separate_main_windows(self):
        other=main.Window();other.show();other.path.setText('second');self.w.path.setText('first')
        try:
            events=self.dispatch(other.search,self.mime([QUrl.fromLocalFile(str(self.folder))]))
            self.assertTrue(all(e.isAccepted() for e in events));self.assertEqual(other.path.text(),str(self.folder.resolve()));self.assertEqual(self.w.path.text(),'first')
        finally:other.close();other.deleteLater()
    def audit_malformed_local_url(self):
        self.w.path.setText('before')
        mime=self.mime([QUrl.fromLocalFile(str(self.folder)+'\0bad')])
        self.assertFalse(any(e.isAccepted() for e in self.dispatch(self.w,mime)));self.assertEqual(self.w.path.text(),'before')
    def audit_real_thread_running(self):
        stop=threading.Event();started=threading.Event()
        class Worker(QThread):
            def run(self):started.set();stop.wait(5)
        worker=Worker();self.w.worker=worker;worker.start();self.assertTrue(started.wait(2))
        try:
            self.assertTrue(worker.isRunning());self.w.path.setText('reading')
            self.assertFalse(any(e.isAccepted() for e in self.dispatch(self.w.search,self.mime([QUrl.fromLocalFile(str(self.folder))]))))
            self.assertEqual(self.w.path.text(),'reading')
        finally:stop.set();worker.wait(2000);self.w.worker=None;worker.deleteLater()

if __name__=='__main__':
    names=[name for name in dir(Audit47) if name.startswith('audit_')]
    r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(Audit47(name) for name in names))
    sys.exit(0 if r.wasSuccessful() else 1)
