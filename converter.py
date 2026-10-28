"""Lossless comic conversion; usable by the desktop app or command line."""
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / '.vendor'))
import img2pdf
import rarfile

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff', '.gif', '.jp2', '.jpx'}


def natural_key(name):
    return [int(s) if s.isdigit() else s.casefold() for s in re.split(r'(\d+)', name)]


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
            partial = Path(temp) / 'result.pdf'
            with partial.open('wb') as stream:
                img2pdf.convert(*pages, outputstream=stream,
                               rotation=img2pdf.Rotation.ifvalid)
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
