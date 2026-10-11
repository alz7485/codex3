"""Treeview cells with partial highlighting, retaining native table behavior."""
import tkinter as tk
from tkinter import ttk, font


class HighlightTree(ttk.Treeview):
    def __init__(self, master, **kwargs):
        self.highlight_column = kwargs.pop('highlight_column', 'original')
        self.highlight_color = kwargs.pop('highlight_color', '#ffd7d7')
        self.highlight_foreground = kwargs.pop('highlight_foreground', '#9b1717')
        super().__init__(master, **kwargs)
        self.highlights = {}
        self.cells = {}
        self.redraw_job = None
        for event in ('<Configure>', '<<TreeviewSelect>>', '<<ThemeChanged>>', '<ButtonRelease-1>', '<B1-Motion>'):
            self.bind(event, self.schedule_redraw, add='+')

    def set_highlights(self, values):
        self.highlights = values
        self.schedule_redraw()

    def schedule_redraw(self, event=None):
        if self.redraw_job is None:
            self.redraw_job = self.after_idle(self.redraw)

    def redraw(self):
        self.redraw_job = None
        if not self.winfo_exists():
            return
        style = ttk.Style(self)
        name = self.cget('style') or 'Treeview'
        text_font = font.Font(self, font=style.lookup(name, 'font') or 'TkDefaultFont')
        row_height = int(style.lookup(name, 'rowheight') or 20)
        visible = {self.identify_row(y) for y in range(0, self.winfo_height(), max(1, row_height // 2))}
        visible.discard('')
        shown = set()
        selected = set(self.selection())
        for iid in visible:
            if iid not in self.highlights:
                continue
            box = self.bbox(iid, self.highlight_column)
            if not box:
                continue
            x, y, width, height = box
            left, right = max(1, x), min(self.winfo_width() - 1, x + width)
            if right <= left:
                continue
            shown.add(iid)
            state = ('selected',) if iid in selected else ()
            background = style.lookup(name, 'background', state) or 'white'
            foreground = style.lookup(name, 'foreground', state) or 'black'
            canvas = self.cells.get(iid)
            if canvas is None:
                canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, takefocus=0)
                self.cells[iid] = canvas
                for event in ('<ButtonPress-1>', '<ButtonRelease-1>', '<MouseWheel>', '<Button-4>', '<Button-5>'):
                    canvas.bind(event, lambda e, sequence=event: self.forward(e, sequence))
            canvas.configure(background=background)
            canvas.place(x=left, y=y, width=right-left, height=height)
            canvas.delete('all')
            text, mask = self.highlights[iid]
            offset = x - left + 4
            start = 0
            while start < len(text):
                remove = mask[start]
                end = start + 1
                while end < len(text) and mask[end] == remove:
                    end += 1
                part = text[start:end]
                measured = text_font.measure(part)
                if remove:
                    canvas.create_rectangle(offset, 1, offset + measured, height - 1, fill=self.highlight_color, outline='', tags='remove')
                canvas.create_text(offset, height/2, text=part, anchor='w', font=text_font, fill=self.highlight_foreground if remove else foreground, tags='text')
                offset += measured
                start = end
        for iid in set(self.cells) - shown:
            self.cells.pop(iid).destroy()

    def forward(self, event, sequence):
        options = {'x': event.x_root-self.winfo_rootx(), 'y': event.y_root-self.winfo_rooty(), 'state': event.state}
        if sequence == '<MouseWheel>':
            options['delta'] = event.delta
        self.event_generate(sequence, **options)
        return 'break'

    def destroy(self):
        if self.redraw_job is not None:
            self.after_cancel(self.redraw_job)
            self.redraw_job = None
        super().destroy()
