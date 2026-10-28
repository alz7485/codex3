"""Render illustrative UI screens on disposable data, without PC/Outlook watchers."""
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import argparse

from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QColor,QFont,QPainter,QPixmap
from companion.ui import InteractionBubble,Mascot,create_application
from companion.core import Notice,Settings
from companion.growth import GrowthEngine,GrowthStore,fresh_progress
from companion.growth_content import load_catalog,seed_content
from companion.growth_ui import GrowthService,GrowthWindow
from companion.content_editor import ContentEditor
from companion.exp_popup import ExpPopup,visual_state


def message_scene(app,output,notice,caption,frame):
    bubble=InteractionBubble();bubble.setFixedWidth(390);bubble.display(notice);bubble.timer.stop()
    bubble.set_tail_above(False);bubble.tail_x=336;bubble.update();app.processEvents()
    mascot=Mascot(100);mascot.frame_index=frame;mascot.previous_frame=None;mascot.show();app.processEvents()
    scene=QPixmap(680,400);scene.fill(QColor('#edf2ef'));p=QPainter(scene)
    p.setFont(QFont(app.font().family(),13));p.setPen(QColor('#344e44'));p.drawText(28,38,caption)
    p.fillRect(0,360,680,40,QColor('#fafcfb'));p.setPen(QColor('#cdd8d1'));p.drawLine(0,360,680,360)
    image=bubble.grab();p.drawPixmap(150,260-image.height(),image);p.drawPixmap(150+336-50,260,mascot.grab());p.end()
    scene.save(str(output));bubble.hide();mascot.hide()



def exp_scene(app,output):
    clock=[1000.];mascot=Mascot(100);mascot.move(436,260);mascot.frame_index=24;mascot.show()
    popup=ExpPopup(mascot,clock=lambda:clock[0]);popup.show_gain(10);popup.timer.stop();app.processEvents()
    frames=[];frame_dir=output/'frames';frame_dir.mkdir(exist_ok=True)
    for index in range(33):
        elapsed=index*.05;clock[0]=1000.+elapsed
        scene=QPixmap(680,400);scene.fill(QColor('#edf2ef'));p=QPainter(scene)
        p.setFont(QFont(app.font().family(),13));p.setPen(QColor('#344e44'));p.drawText(28,38,'EXP獲得：頭の近くで上へスライドして消える')
        p.fillRect(0,360,680,40,QColor('#fafcfb'));p.setPen(QColor('#cdd8d1'));p.drawLine(0,360,680,360)
        p.drawPixmap(436,260,mascot.grab())
        rise,_=visual_state(elapsed);p.drawPixmap(436+50-popup.width()//2,round(260+popup.start_offset-rise),popup.grab())
        p.end()
        if index==12:scene.save(str(output/'exp-gain.png'))
        path=frame_dir/f'exp_{index:02}.png';scene.save(str(path));frames.append(path)
    try:
        from PIL import Image
        images=[Image.open(p).convert('RGB') for p in frames]
        images[0].save(output/'exp-gain.gif',save_all=True,append_images=images[1:],duration=[50]*32+[750],loop=0,disposal=2)
    except ImportError:
        print('PNG frames saved. Pillow is optional for GIF export.')
    popup.cancel();mascot.hide();popup.deleteLater();mascot.deleteLater()


def capture(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);app=create_application()
    exp_scene(app,output)
    message_scene(app,output/'level-up.png',Notice('','Lv.2になりました。\n一緒に過ごした記録から、解放したものを確認できます。',True,expression='happy',kind='notification'),'レベルアップ：実装済みのメッセージ',2)
    with TemporaryDirectory(prefix='yohaku-growth-preview-') as temporary:
        root=Path(temporary);seed_content(root/'content');catalog=load_catalog(root/'content')
        p=fresh_progress();p.update(exp=65.,level=2,seconds=3720.,exp_seconds=120.,days=['2026-10-28'],unlocked=list(catalog.all_items),equipped={'accessory':'base:welcome_pin'},
            trophies={'base:first_hour':{'at':'2026-10-28T16:00:00+09:00','exp':5}},best={'base:first_hour':62.})
        service=GrowthService.__new__(GrowthService);service.host=SimpleNamespace(settings=Settings(character='A'))
        service.error='';service.store=GrowthStore(root/'growth.json');service.content_root=root/'content'
        service.engine=GrowthEngine(service.store,catalog,lambda:1000.);service.engine.data['characters']['A']=p
        service.error_text=lambda:'プレビュー用のサンプル値です。実際の記録ではありません。'
        window=GrowthWindow(service);window.resize(900,720);window.show();app.processEvents();window.grab().save(str(output/'status.png'));window.hide()
        editor=ContentEditor(root/'content');editor.resize(1360,860);editor.kind.setCurrentIndex(editor.kind.findData('costumes'));editor.show();app.processEvents()
        editor.grab().save(str(output/'content-editor.png'));editor.hide();editor.deleteLater();window.deleteLater();app.processEvents()
    print(str(output))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='docs/growth-preview');args=parser.parse_args();capture(args.output)
