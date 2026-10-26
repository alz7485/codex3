"""PDF printing through Qt's printer selection dialog; no external commands."""
import math
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QRectF, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog

from .file_drop import FileDropError, regular_file


def print_pdf(path, parent=None, on_dialog=None):
    path = regular_file(path)
    if path.suffix.lower() != '.pdf' or path.stat().st_size > 256 * 1024 * 1024:
        raise FileDropError('印刷は256MiB以内のPDFを選んでください。')
    document = QPdfDocument(parent)
    device = QFile(str(path))
    painter = None
    dialog = None
    try:
        if not device.open(QIODevice.OpenModeFlag.ReadOnly):
            raise FileDropError('PDFを読み込めません。')
        document.load(device)
        if document.status() != QPdfDocument.Status.Ready or not 1 <= document.pageCount() <= 1000:
            raise FileDropError('PDFを開けません。暗号化されたPDFや1,000ページを超えるPDFは対象外です。')
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(path.name)
        dialog = QPrintDialog(printer, parent); dialog.setWindowTitle('Yohaku — PDFを印刷')
        dialog.setMinMax(1, document.pageCount())
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintSelection, False)
        dialog.setOption(QPrintDialog.PrintDialogOption.PrintCurrentPage, False)
        if on_dialog is not None:
            on_dialog(dialog)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False
        painter = QPainter()
        if not painter.begin(printer):
            raise FileDropError('プリンターを開始できません。')
        ranged = printer.printRange() == QPrinter.PrintRange.PageRange
        first = max(1, printer.fromPage() or 1) if ranged else 1
        last = min(document.pageCount(), printer.toPage() or document.pageCount()) if ranged else document.pageCount()
        pages = list(range(first-1, last))
        if printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
            pages.reverse()
        for offset, page in enumerate(pages):
            if offset and not printer.newPage():
                raise FileDropError('次のページを印刷できません。プリンターを確認してください。')
            points = document.pagePointSize(page)
            if any(not math.isfinite(v) or v <= 0 for v in (points.width(), points.height())):
                raise FileDropError('PDFのページサイズが不正です。')
            scale = min(300/72, 4096/max(points.width(), points.height()))
            pixels = QSize(max(1, round(points.width()*scale)), max(1, round(points.height()*scale)))
            image = document.render(page, pixels)
            if image.isNull():
                raise FileDropError('PDFのページを描画できません。')
            rect = QRectF(0, 0, printer.width(), printer.height())
            target = image.size().scaled(rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
            box = QRectF(rect.x()+(rect.width()-target.width())/2,
                         rect.y()+(rect.height()-target.height())/2, target.width(), target.height())
            painter.drawImage(box, image)
        ended = painter.end(); painter = None
        if not ended or printer.printerState() in (QPrinter.PrinterState.Error, QPrinter.PrinterState.Aborted):
            raise FileDropError('印刷データの送信を完了できません。プリンターを確認してください。')
        return True
    finally:
        if painter is not None and painter.isActive():
            painter.end()
        document.close()
        device.close()  # Release the native handle immediately, before deferred QObject deletion.
        document.deleteLater()
        if dialog is not None:
            dialog.deleteLater()
