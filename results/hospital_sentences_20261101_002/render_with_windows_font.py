"""Run scripts/render_sequences.py unchanged on WSL, where the Linux CJK label font is missing (no sudo).

Only the label font falls back to the Windows Microsoft YaHei file; poses, timing and frames are untouched.
render_sequences.py is part of the sequence identity, so it is wrapped instead of edited.
Usage (repository root): .venv/bin/python results/hospital_sentences_20261101_001/render_with_windows_font.py --run-dir ... --output ...
"""
from pathlib import Path
import runpy
import sys

from PIL import ImageFont

LINUX_FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
WINDOWS_FONT = '/mnt/c/Windows/Fonts/msyh.ttc'
_truetype = ImageFont.truetype


def truetype(font=None, size=10, *args, **kwargs):
    if font == LINUX_FONT and not Path(LINUX_FONT).exists():
        font = WINDOWS_FONT
    return _truetype(font, size, *args, **kwargs)


ImageFont.truetype = truetype
sys.argv = ['scripts/render_sequences.py', *sys.argv[1:]]
runpy.run_path('scripts/render_sequences.py', run_name='__main__')
