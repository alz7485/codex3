# Third-party software

The Windows onedir build uses Python, PySide6 / Qt 6, shiboken6 and pywin32.
PyInstaller is used to build the application.

- Python: Python Software Foundation License, https://docs.python.org/3/license.html
- PySide6 / Qt for Python: LGPLv3 / GPLv3 / commercial licensing, https://doc.qt.io/qtforpython-6/licenses.html
- Qt 6: component-specific LGPL / GPL / third-party licenses, https://doc.qt.io/qt-6/licenses.html
- pywin32: PSF-style license, https://github.com/mhammond/pywin32
- PyInstaller: GPL with the bootloader exception permitting distribution of generated bundles, https://pyinstaller.org/en/stable/license.html
- pyzipper: MIT License, https://github.com/danifus/pyzipper
- PyCryptodome / pycryptodomex: BSD and public-domain components, https://www.pycryptodome.org/src/license

The build script copies license texts available in installed distribution metadata
into `third-party-licenses/` in the onedir folder. Keep that folder with the
distribution. The executable uses the packaged Qt/Python libraries in `_internal/`.
The original Yohaku source and build scripts accompany the source ZIP.

7z support uses py7zr (LGPL-2.1-or-later), https://github.com/miurahr/py7zr .
Its installed compression-library license texts are also copied into third-party-licenses/.
