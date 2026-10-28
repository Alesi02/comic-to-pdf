import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from converter import convert
import pikepdf
from PIL import Image


class ConversionTests(unittest.TestCase):
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
