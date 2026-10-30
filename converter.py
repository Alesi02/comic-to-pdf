"""Lossless comic conversion; usable by the desktop app or command line."""
import os
import re
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / '.vendor'))
import img2pdf
import rarfile
import pikepdf

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.jp2', '.jpx'}


def natural_key(name):
    return [int(s) if s.isdigit() else s.casefold() for s in re.split(r'(\d+)', name)]


def normalize_page_heights(source, destination):
    """Change PDF placement only; keep embedded image streams untouched."""
    with pikepdf.open(source) as pdf:
        dimensions = []
        for page in pdf.pages:
            x0, y0, x1, y1 = map(float, page.MediaBox)
            width, height = x1 - x0, y1 - y0
            rotated = int(page.obj.get('/Rotate', 0)) % 180 == 90
            dimensions.append((width, height, x0, y0, rotated))
        # Round away insignificant PDF decimal differences. Ties use the first
        # height encountered in reading order.
        heights = [round(w if rotated else h, 6)
                   for w, h, _, _, rotated in dimensions]
        target_height = Counter(heights).most_common(1)[0][0]
        for page, (width, height, x0, y0, rotated), visible_height in zip(
                pdf.pages, dimensions, heights):
            if visible_height == target_height:
                continue
            scale = target_height / (width if rotated else height)
            transform = f'q {scale:.12g} 0 0 {scale:.12g} {-x0 * scale:.12g} {-y0 * scale:.12g} cm\n'
            page.contents_add(pikepdf.Stream(pdf, transform.encode('ascii')), prepend=True)
            page.contents_add(pikepdf.Stream(pdf, b'\nQ\n'))
            page.MediaBox = [0, 0, width * scale, height * scale]
            # img2pdf normally sets no CropBox; keep it consistent if present.
            if '/CropBox' in page.obj:
                page.CropBox = page.MediaBox
        pdf.save(destination)


def convert(source, destination, progress=lambda message: None):
    source, destination = Path(source), Path(destination)
    if source.suffix.lower() not in {'.cbz', '.cbr'}:
        raise ValueError('Choose a CBZ or CBR comic archive.')
    destination.mkdir(parents=True, exist_ok=True)
    # Detect ZIP by contents: some CBR files are actually ZIP archives.
    if zipfile.is_zipfile(source):
        archive = zipfile.ZipFile(source)
        names = [i.filename for i in archive.infolist() if not i.is_dir()]
    else:
        rarfile.BSDTAR_TOOL = 'tar'
        rarfile.tool_setup(bsdtar=True)
        archive = rarfile.RarFile(source)
        names = [i.filename for i in archive.infolist() if not i.isdir()]
    try:
        names = sorted((n for n in names if Path(n).suffix.lower() in EXTENSIONS
                        and '__MACOSX' not in n.split('/') and not Path(n).name.startswith('._')),
                       key=natural_key)
        if not names:
            raise ValueError('This archive contains no supported images.')
        with tempfile.TemporaryDirectory(prefix='comic-pdf-') as temp:
            pages = []
            for index, name in enumerate(names, 1):
                progress(f'Reading image {index} of {len(names)}')
                # Generated names prevent archive paths from escaping the temporary folder.
                page = Path(temp) / f'{index:06d}{Path(name).suffix.lower()}'
                with archive.open(name) as src, page.open('wb') as dst:
                    import shutil
                    shutil.copyfileobj(src, dst)
                pages.append(str(page))
            progress(f'Writing PDF · {len(pages)} images')
            initial = Path(temp) / 'initial.pdf'
            with initial.open('wb') as stream:
                img2pdf.convert(*pages, outputstream=stream,
                               # Image DPI metadata can be absent or inconsistent.
                               # Set physical page size without resampling pixels.
                               layout_fun=img2pdf.get_fixed_dpi_layout_fun((300, 300)),
                               rotation=img2pdf.Rotation.ifvalid)
            progress('Making all page heights consistent')
            partial = Path(temp) / 'result.pdf'
            normalize_page_heights(initial, partial)
            # Exclusive creation protects existing PDFs, including simultaneous conversions.
            number = 0
            while True:
                suffix = f' ({number})' if number else ''
                target = destination / f'{source.stem}{suffix}.pdf'
                try:
                    out = target.open('xb')
                    break
                except FileExistsError:
                    number += 1
            try:
                with out, partial.open('rb') as src:
                    shutil.copyfileobj(src, out)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
        return target, len(names)
    finally:
        archive.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Convert comic archives without lossy image recompression.')
    parser.add_argument('files', nargs='+', type=Path)
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'output')
    args = parser.parse_args()
    for file in args.files:
        target, count = convert(file, args.output, print)
        print(f'Saved {count} pages: {target}')
