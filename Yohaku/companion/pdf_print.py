"""Direct PDF printing to the Windows default printer, without print dialogs."""
import math
from PySide6.QtCore import QFile, QIODevice, QRectF, QSize
from PySide6.QtGui import QPageLayout, QPageSize, QPainter
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo
from .file_drop import FileDropError, regular_file


def page_layout(points, mode):
    width,height=points.width(),points.height()
    if mode not in ('a4','a3','auto') or any(not math.isfinite(v) or v<=0 for v in (width,height)):
        raise FileDropError('PDFのページサイズまたは用紙の指定が不正です。')
    # A4 point dimensions differ by rounding between PDF generators. Treat up
    # to one point of rounding as A4; B4 and larger are scaled to A3.
    short,long=sorted((width,height))
    paper=QPageSize.PageSizeId.A4 if mode=='a4' or mode=='auto' and short<=596.3 and long<=842.9 else QPageSize.PageSizeId.A3
    orientation=QPageLayout.Orientation.Landscape if width>height else QPageLayout.Orientation.Portrait
    return QPageSize(paper),orientation


def render_page(document,page):
    points=document.pagePointSize(page)
    page_layout(points,'auto')
    scale=min(300/72,4096/max(points.width(),points.height()))
    image=document.render(page,QSize(max(1,round(points.width()*scale)),max(1,round(points.height()*scale))))
    if image.isNull():raise FileDropError('PDFのページを描画できません。')
    return image


def default_printer():
    info=QPrinterInfo.defaultPrinter()
    if info.isNull():raise FileDropError('Windowsの既定プリンターを設定してください。')
    printer=QPrinter(info,QPrinter.PrinterMode.HighResolution)
    printer.setResolution(300);printer.setCopyCount(1)
    return printer,info.supportedPageSizes()


def print_pdf(path,paper='auto'):
    path=regular_file(path)
    if paper not in ('a4','a3','auto'):raise FileDropError('用紙はA4・A3・自動から選んでください。')
    if path.suffix.lower()!='.pdf' or path.stat().st_size>256*1024*1024:
        raise FileDropError('印刷は256MiB以内のPDFを選んでください。')
    document=QPdfDocument();device=QFile(str(path));painter=None;printer=None;started=False;complete=False
    try:
        if not device.open(QIODevice.OpenModeFlag.ReadOnly):raise FileDropError('PDFを読み込めません。')
        document.load(device)
        if document.status()!=QPdfDocument.Status.Ready or not 1<=document.pageCount()<=1000:
            raise FileDropError('PDFを開けません。暗号化されたPDFや1,000ページを超えるPDFは対象外です。')
        printer,supported=default_printer();printer.setDocName(path.name)
        layouts=[];color=False
        # Validate every page before submitting anything. Choose job colour from
        # the actual bounded-resolution render, not a preview or filename.
        for page in range(document.pageCount()):
            size,orientation=page_layout(document.pagePointSize(page),paper)
            if supported and not any(entry.id()==size.id() or entry.isEquivalentTo(size) for entry in supported):
                raise FileDropError('既定プリンターが選択した用紙に対応していません。')
            layouts.append((size,orientation))
            image=render_page(document,page)
            color=color or not image.allGray()
        printer.setColorMode(QPrinter.ColorMode.Color if color else QPrinter.ColorMode.GrayScale)
        painter=QPainter()
        for page,(size,orientation) in enumerate(layouts):
            # Windows print engines apply the layout for the NEXT page when it
            # is changed before newPage(). Preserve driver printable margins.
            layout=printer.pageLayout();layout.setPageSize(size);layout.setOrientation(orientation)
            if not printer.setPageLayout(layout):raise FileDropError('プリンターの用紙サイズを変更できません。')
            if page==0:
                if not painter.begin(printer):raise FileDropError('プリンターを開始できません。')
                started=True;painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            elif not printer.newPage():raise FileDropError('次のページを印刷できません。')
            image=render_page(document,page)
            width,height=printer.width(),printer.height()
            scale=min(width/image.width(),height/image.height())
            rect=QRectF((width-image.width()*scale)/2,(height-image.height()*scale)/2,image.width()*scale,image.height()*scale)
            painter.drawImage(rect,image)
        ended=painter.end();painter=None
        if not ended or printer.printerState() in (QPrinter.PrinterState.Error,QPrinter.PrinterState.Aborted):
            raise FileDropError('印刷データの送信を完了できません。プリンターを確認してください。')
        complete=True;return True
    except FileDropError as error:
        if started:raise FileDropError(str(error)+' 一部のページが送信済みの場合があります。') from None
        raise
    finally:
        if started and not complete and printer is not None:printer.abort()
        if painter is not None and painter.isActive():painter.end()
        document.close();device.close()
