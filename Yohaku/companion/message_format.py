"""Bounded text ranges and escaped rich text; no user HTML or CSS execution."""
from copy import deepcopy
from html import escape
import re

ACCENT = '#245ca6'
IMPORTANT = re.compile(r'(?<!\d)(?:[01]?\d|2[0-3]):[0-5]\d(?!\d)|\d{1,4}[/-]\d{1,2}(?:[/-]\d{1,2})?|\d+時間(?:\d+分)?|\d+分|\d+時(?:\d+分)?|\d+月\d+日|メール')


def validate_styles(text, styles):
    if not isinstance(styles, list) or len(styles) > 100:
        raise ValueError('文字の装飾は100区間まで指定できます。')
    end = 0
    for row in styles:
        if (not isinstance(row, dict) or set(row) != {'start','length','bold','color'}
                or type(row['start']) is not int or type(row['length']) is not int
                or row['start'] < end or row['length'] <= 0 or row['start']+row['length'] > len(text)
                or type(row['bold']) is not bool or not isinstance(row['color'], str)
                or row['color'] and not re.fullmatch(r'#[0-9a-fA-F]{6}', row['color'])):
            raise ValueError('文字装飾の範囲・太字・色の指定が不正です。')
        end = row['start']+row['length']
    return deepcopy(styles)


def trimmed_styles(text, styles):
    validate_styles(text, styles)
    begin = len(text)-len(text.lstrip()); length = len(text.strip()); result = []
    for row in styles:
        left = max(row['start'], begin); right = min(row['start']+row['length'], begin+length)
        if left < right:
            result.append(dict(row, start=left-begin, length=right-left))
    return result


def message_html(text, automatic=True, styles=()):
    formats = [(False, '') for _ in text]
    if automatic:
        for match in IMPORTANT.finditer(text):
            for index in range(*match.span()): formats[index] = (True, ACCENT)
    for row in validate_styles(text, list(styles)):
        for index in range(row['start'], row['start']+row['length']):
            formats[index] = (row['bold'], row['color'])
    output=[]; start=0
    while start < len(text):
        end=start+1
        while end < len(text) and formats[end] == formats[start]:end+=1
        bold,color=formats[start]; value=escape(text[start:end]).replace('\n','<br/>')
        if bold:value='<b>'+value+'</b>'
        if color:value=f'<span style="color:{color}">'+value+'</span>'
        output.append(value);start=end
    # Preserve spaces/newlines while letting Qt wrap at the available width.
    return '<div style="white-space:pre-wrap">'+''.join(output)+'</div>'
