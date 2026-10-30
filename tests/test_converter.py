import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from converter import convert
import pikepdf
from PIL import Image


class ConversionTests(unittest.TestCase):
    def test_common_height_preserves_ratios_and_jpeg_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            comic = folder / 'different-heights.cbz'
            sizes = [(100, 100), (150, 225), (150, 225), (300, 450), (300, 225)]
            originals = []
            with zipfile.ZipFile(comic, 'w') as archive:
                for index, size in enumerate(sizes):
                    data = io.BytesIO()
                    Image.new('RGB', size, (index * 40, 127, 221)).save(data, 'JPEG')
                    originals.append(data.getvalue())
                    archive.writestr(f'{index}.jpg', originals[-1])
            target, _ = convert(comic, folder)
            with pikepdf.open(target) as pdf:
                for index, page in enumerate(pdf.pages):
                    width, height = map(float, list(page.MediaBox)[2:])
                    self.assertAlmostEqual(height, 54)
                    self.assertAlmostEqual(width / height, sizes[index][0] / sizes[index][1])
                    image = list(page.Resources.XObject.values())[0]
                    self.assertEqual(image.read_raw_bytes(), originals[index])
                    self.assertEqual((image.Width, image.Height), sizes[index])
                self.assertEqual(list(pdf.pages[1].MediaBox), [0, 0, 36, 54])

    def test_height_tie_uses_first_page(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            comic = folder / 'tie.cbz'
            with zipfile.ZipFile(comic, 'w') as archive:
                for index, size in enumerate([(100, 200), (100, 300)]):
                    data = io.BytesIO()
                    Image.new('RGB', size).save(data, 'PNG')
                    archive.writestr(f'{index}.png', data.getvalue())
            target, _ = convert(comic, folder)
            with pikepdf.open(target) as pdf:
                for page in pdf.pages:
                    self.assertAlmostEqual(float(page.MediaBox[3]), 48)

    def test_page_size_ignores_inconsistent_dpi(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            originals = []
            comic = folder / 'mixed-dpi.cbz'
            with zipfile.ZipFile(comic, 'w') as archive:
                for index, dpi in enumerate([(300, 300), None, (72, 72), (150, 300)]):
                    data = io.BytesIO()
                    image = Image.new('RGB', (150, 225), (index * 50, 127, 221))
                    image.save(data, 'JPEG', **({'dpi': dpi} if dpi else {}))
                    originals.append(data.getvalue())
                    archive.writestr(f'{index}.jpg', originals[-1])
                # A spread retains its wider aspect ratio and original pixels.
                data = io.BytesIO()
                Image.new('RGB', (300, 225)).save(data, 'JPEG', dpi=(72, 72))
                originals.append(data.getvalue())
                archive.writestr('4.jpg', originals[-1])
            target, count = convert(comic, folder)
            self.assertEqual(count, 5)
            with pikepdf.open(target) as pdf:
                for index, page in enumerate(pdf.pages):
                    expected = [0, 0, 72, 54] if index == 4 else [0, 0, 36, 54]
                    self.assertEqual(list(page.MediaBox), expected)
                    obj = list(page.Resources.XObject.values())[0]
                    self.assertEqual(obj.read_raw_bytes(), originals[index])

    def test_lossless_images_order_and_collision(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            jpeg, png = io.BytesIO(), io.BytesIO()
            image = Image.new('RGB', (40, 60), (31, 127, 221))
            image.save(jpeg, 'JPEG')
            image.save(png, 'PNG')
            comic = folder / 'test.cbz'
            with zipfile.ZipFile(comic, 'w') as archive:
                archive.writestr('10.png', png.getvalue())
                archive.writestr('2.jpg', jpeg.getvalue())
                archive.writestr('ComicInfo.xml', '<ComicInfo/>')
            target, count = convert(comic, folder)
            original = target.read_bytes()
            other, _ = convert(comic, folder)
            self.assertNotEqual(target, other)
            self.assertEqual(original, target.read_bytes())
            self.assertEqual(count, 2)
            with pikepdf.open(target) as pdf:
                self.assertEqual(len(pdf.pages), 2)
                first = list(pdf.pages[0].Resources.XObject.values())[0]
                second = list(pdf.pages[1].Resources.XObject.values())[0]
                self.assertEqual(first.read_raw_bytes(), jpeg.getvalue())
                for obj in (first, second):
                    self.assertEqual((obj.Width, obj.Height), image.size)
                decoded = pikepdf.PdfImage(second).as_pil_image().convert('RGB')
                self.assertEqual(decoded.tobytes(), image.tobytes())

    def test_archive_without_images(self):
        with tempfile.TemporaryDirectory() as folder:
            comic = Path(folder) / 'empty.cbz'
            with zipfile.ZipFile(comic, 'w') as archive:
                archive.writestr('note.txt', 'No images')
            with self.assertRaisesRegex(ValueError, 'no supported images'):
                convert(comic, folder)
            self.assertEqual(list(Path(folder).glob('*.pdf')), [])

    def test_invalid_extension(self):
        with self.assertRaisesRegex(ValueError, 'CBZ or CBR'):
            convert('file.txt', '.')


if __name__ == '__main__':
    unittest.main()
