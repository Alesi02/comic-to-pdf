# Comic to PDF

A local app that converts CBZ and CBR comic archives into PDFs without resizing images or applying lossy recompression. Choose multiple files or drag them into the browser window.

## Getting started (Windows)

1. Install **Python 3.12 or newer** from [python.org](https://www.python.org/downloads/windows/), including the Python launcher.
2. Download this repository using **Code → Download ZIP**, then extract it.
3. Double-click **Start.cmd**. On the first launch, the app creates a local Python environment and installs its dependencies. Internet access is needed for this initial setup.
4. The app opens in your default browser. Keep the launcher window open while using it; close the window when finished.

## Convert comics

1. Click **Choose comic files**, or drag `.cbz` and `.cbr` files onto the drop area. Select files from any folder; no special input folder is needed.
2. Click **Convert to PDF**.
3. Click **Open output folder** to find the finished PDFs in the project's `output` folder.

Each archive produces a separate PDF. Original files remain untouched. Existing PDFs are preserved using numbered filenames. Pages follow natural filename order (2 before 10).

## Image quality

Original pixel dimensions are retained. There is no resizing or lossy recompression. JPEG image bytes are embedded unchanged; other supported formats are embedded directly where possible or stored with lossless compression. PDF size can increase. Valid image orientation metadata is respected. Animated or multipage images may produce multiple PDF pages.

Supported image extensions: JPEG, PNG, WebP, BMP, TIFF, GIF and JPEG 2000. Non-image entries are ignored. A supported image that cannot be decoded causes conversion to fail with an error beside its file.

Every page in a PDF has the same height: the most common page height calculated at 300 DPI, ignoring image DPI metadata. If heights tie, the first height in reading order wins. Each page's width is adjusted proportionally to preserve the original image's aspect ratio, including wider spreads. Pages already at the chosen height retain their size. This changes PDF placement only; image pixels are never resampled or recompressed.

## Privacy and offline use

After setup, conversion works offline. The app listens only on `127.0.0.1` and sends no comics to an external service. Files selected in the browser are transferred only to the local app on the same computer. Temporary copies are removed after conversion.

## CBR support

CBR extraction requires a compatible RAR reader. Windows 10/11 includes `tar`, which the app can use; 7-Zip or UnRAR can also be used when available on PATH. Encrypted, multipart or unusual archives are not guaranteed to work. Errors appear beside the affected file.

## Command line

With dependencies installed:

```console
python -m pip install -r requirements.txt
python converter.py "comic.cbz" --output "output"
```

The browser launcher and **Open output folder** button target Windows.

## Tests

Run `python -m unittest discover -s tests -v` with dependencies installed. Tests create their own images and archives, checking page ordering, JPEG byte preservation, lossless PNG pixels, filename collision handling and invalid archives.
