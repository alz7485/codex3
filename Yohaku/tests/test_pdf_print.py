"""Windows direct-print paths, using only a synthetic PDF output device."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import QFile,QIODevice,QSizeF
from PySide6.QtGui import QColor,QPageLayout,QPageSize,QPainter,QPdfWriter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter,QPrintDialog
from companion.file_drop import FileDropError
from companion.pdf_print import configure_page,page_layout,print_pdf
from companion.ui import create_application

class DirectPrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup);self.root=Path(self.temporary.name)
    def pdf(self,pages=None,color=False):
        path=self.root/'input.pdf';writer=QPdfWriter(str(path));pages=pages or [QPageSize.PageSizeId.A4]
        writer.setPageSize(QPageSize(pages[0]));p=QPainter(writer)
        for i,size in enumerate(pages):
            if i:writer.setPageSize(QPageSize(size));writer.newPage()
            p.setPen(QColor('red' if color else 'black'));p.drawText(100,200,'Synthetic test');p.drawRect(100,300,400,400)
        p.end();del writer;return path
    def output_printer(self,supported=None):
        printer=QPrinter(QPrinter.PrinterMode.HighResolution);printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(self.root/'output.pdf'));printer.setResolution(300)
        return printer,supported or []
    def sizes(self,path):
        doc=QPdfDocument();device=QFile(str(path));self.assertTrue(device.open(QIODevice.OpenModeFlag.ReadOnly))
        try:
            doc.load(device);self.assertEqual(doc.status(),QPdfDocument.Status.Ready)
            return [doc.pagePointSize(i) for i in range(doc.pageCount())]
        finally:doc.close();device.close()
    def test_auto_uses_a4_for_small_pages_and_a3_for_intermediate_and_larger_pages(self):
        for width,height,expected in [(595.28,841.89,'A4'),(420,595,'A4'),(1008,729,'A3'),(2384,3370,'A3'),(841.89,595.28,'A4')]:
            size,orientation=page_layout(QSizeF(width,height),'auto')
            self.assertEqual(size.id(),getattr(QPageSize.PageSizeId,expected))
            self.assertEqual(orientation,QPageLayout.Orientation.Landscape if width>height else QPageLayout.Orientation.Portrait)
        self.assertEqual(page_layout(QSizeF(2000,3000),'a4')[0].id(),QPageSize.PageSizeId.A4)
        self.assertEqual(page_layout(QSizeF(100,100),'a3')[0].id(),QPageSize.PageSizeId.A3)
        for dimensions in [(0,10),(float('inf'),10),(float('nan'),10)]:
            with self.assertRaises(FileDropError):page_layout(QSizeF(*dimensions),'auto')
    def test_auto_mixed_page_sizes_prints_all_pages_without_a_dialog(self):
        source=self.pdf([QPageSize.PageSizeId.A4,QPageSize.PageSizeId.A0]);printer,_=self.output_printer()
        with patch('companion.pdf_print.default_printer',return_value=(printer,[])),patch.object(QPrintDialog,'exec',side_effect=AssertionError('No dialog')):
            self.assertTrue(print_pdf(source,'auto'))
        sizes=self.sizes(self.root/'output.pdf');self.assertEqual(len(sizes),2)
        self.assertAlmostEqual(sizes[0].width(),595,delta=2);self.assertAlmostEqual(sizes[1].width(),842,delta=2)
        moved=source.with_name('unlocked.pdf');source.rename(moved);moved.rename(source)
    def test_explicit_size_and_color_are_automatic_from_document(self):
        for color in (False,True):
            source=self.pdf(color=color);printer,_=self.output_printer()
            with patch('companion.pdf_print.default_printer',return_value=(printer,[])):self.assertTrue(print_pdf(source,'a3'))
            self.assertEqual(printer.colorMode(),QPrinter.ColorMode.Color if color else QPrinter.ColorMode.GrayScale)
            self.assertAlmostEqual(self.sizes(self.root/'output.pdf')[0].width(),842,delta=2)
    def test_unsupported_later_page_and_bad_pdf_submit_nothing(self):
        source=self.pdf([QPageSize.PageSizeId.A4,QPageSize.PageSizeId.A3]);printer,_=self.output_printer()
        with patch('companion.pdf_print.default_printer',return_value=(printer,[QPageSize(QPageSize.PageSizeId.A4)])):
            with self.assertRaises(FileDropError):print_pdf(source,'auto')
        self.assertFalse((self.root/'output.pdf').exists())
        source.write_bytes(b'invalid')
        with patch('companion.pdf_print.default_printer') as factory:
            with self.assertRaises(FileDropError):print_pdf(source,'a4')
            factory.assert_not_called()
    def test_no_default_printer_returns_clear_error_without_dialogs(self):
        from companion.pdf_print import default_printer
        from PySide6.QtPrintSupport import QPrinterInfo
        with patch('companion.pdf_print.QPrinterInfo.defaultPrinter',return_value=QPrinterInfo()):
            with self.assertRaisesRegex(FileDropError,'既定プリンター'):default_printer()

    def test_native_driver_rejecting_full_layout_uses_individual_properties(self):
        class NativeDriver:
            def __init__(self):self.layout=QPageLayout();self.layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            def printerState(self):return QPrinter.PrinterState.Idle
            def pageLayout(self):return QPageLayout(self.layout)
            def setPageLayout(self,layout):raise AssertionError('Full layout must not be submitted')
            def setPageSize(self,size):self.layout.setPageSize(size);return False  # Return code alone is not authoritative.
            def setPageOrientation(self,value):self.layout.setOrientation(value)
        printer=NativeDriver();size=QPageSize(QPageSize.PageSizeId.A3)
        configure_page(printer,size,QPageLayout.Orientation.Landscape)
        self.assertEqual(printer.pageLayout().pageSize().id(),QPageSize.PageSizeId.A3)
        self.assertEqual(printer.pageLayout().orientation(),QPageLayout.Orientation.Landscape)

    def test_driver_that_ignores_size_change_is_rejected_before_printing(self):
        from unittest.mock import Mock
        layout=QPageLayout();layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        driver=Mock();driver.pageLayout.return_value=layout
        with self.assertRaises(FileDropError):configure_page(driver,QPageSize(QPageSize.PageSizeId.A3),QPageLayout.Orientation.Portrait)
        driver.setPageLayout.assert_not_called()

    def test_active_windows_job_queues_engine_properties_for_next_sheet(self):
        from PySide6.QtPrintSupport import QPrintEngine
        class ActiveNativeDriver:
            def __init__(self):self.layout=QPageLayout();self.layout.setPageSize(QPageSize(QPageSize.PageSizeId.A4));self.calls=[]
            def pageLayout(self):return QPageLayout(self.layout)
            def printerState(self):return QPrinter.PrinterState.Active
            def outputFormat(self):return QPrinter.OutputFormat.NativeFormat
            def setPageSize(self,value):raise AssertionError('Public setter rejects active native jobs')
            def setPageOrientation(self,value):raise AssertionError('Public setter rejects active native jobs')
            def printEngine(self):return self
            def setProperty(self,key,value):
                self.calls.append(key)
                if key==QPrintEngine.PrintEnginePropertyKey.PPK_QPageSize:self.layout.setPageSize(value)
                else:self.layout.setOrientation(QPageLayout.Orientation(value))
        driver=ActiveNativeDriver()
        configure_page(driver,QPageSize(QPageSize.PageSizeId.A3),QPageLayout.Orientation.Landscape)
        self.assertEqual(len(driver.calls),2)
        self.assertEqual(driver.layout.pageSize().id(),QPageSize.PageSizeId.A3)
        self.assertEqual(driver.layout.orientation(),QPageLayout.Orientation.Landscape)
