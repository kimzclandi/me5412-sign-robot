"""Static PDF fallback for the editable artifact-tool slide builder.

Inputs: twelve or fourteen rendered slide PNGs. Output: a 16:9 image-only PDF.
This preserves pixels, not editable text; the PPTX remains the editable master.
"""
from pathlib import Path
import re
import sys

from PIL import Image
from pypdf import PdfReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
revision = sys.argv[1] if len(sys.argv) > 1 else "v1"
if not re.fullmatch(r"v\d+", revision):
    raise ValueError("revision must be v followed by an integer")
upgraded = int(revision[1:]) >= 4
output = ROOT / (f"deliverables/course-report-{revision}" if upgraded else "deliverables/course-report-v1")
page_count = 14 if upgraded else 12
target = output / f"ME5412_Text_to_Robot_Signing_{revision}.pdf"
pdf = canvas.Canvas(str(target), pagesize=(960, 540))
pdf.setTitle("ME5412 Text to Robot Signing - static slide preview")
for index in range(1, page_count + 1):
    preview = output / "previews" / f"slide-{index:02}.png"
    pdf.drawImage(str(preview), 0, 0, width=960, height=540)
    pdf.showPage()
pdf.save()
reader = PdfReader(target)
assert len(reader.pages) == page_count
for index, page in enumerate(reader.pages, 1):
    assert tuple(float(x) for x in page.mediabox[2:]) == (960, 540)
    images = list(page.images)
    assert len(images) == 1
    source = Image.open(output / "previews" / f"slide-{index:02}.png").convert("RGB")
    embedded = images[0].image.convert("RGB")
    assert source.size == embedded.size
    assert source.tobytes() == embedded.tobytes()
print(target)
