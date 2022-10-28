# HighFinesse Wavemeter Client
This project provides a python wrapper around the HighFinesse Wavemeter NetApi. It uses Rust to create bindings to the C interface provided by HighFinesse and exposes a subset in safe way to python.

## Requirements
- Rust installation (https://rustup.rs/)
- LLVM/Clang installation (https://github.com/llvm/llvm-project/releases/)
- MS Visual Studio Buildtools (https://visualstudio.microsoft.com/de/visual-cpp-build-tools/)
- Python 3.6 installation or higher (https://www.python.org/downloads/)
- Python package `maturin` (https://pypi.org/project/maturin/)

## Library
The header and import library from HighFinesse can be found on the server pc, which has the official software installed. The header is located at:
`<wavemeter install dir>/Projects/Headers/C/wlmData.h` and the import library at `<wavemeter install dir>/Projects/Headers/C/64/wlmData.lib`.

For convenience both are included in this repository in the `include/` and `lib/` directories.

## Building the Python lib
With all the requirements installed and the HighFinesse library inplace, a python wheel can be build using:
```
maturin build
```
If everything worked out a python 3.6+ compatible wheel can be found in the `target/wheel/` directory. This wheel can then be install as regular python package using
```
pip install <wheel name>
```

## Usage
The generated python package is called `wavemeter`. The exported functions are part of the `WaveMeter` object.
```python
from wavemeter import WaveMeter

<function value> = WaveMeter.<function name>(<function args>)
```
The official documentation of all library functions can be found in the wavemeter manual (p. 62 and following), located in `<wavemeter install dir>`.

The functions exported by this python package can either be found interactively in an `ipython` shell via tab completion, or generated from the rust source using `cargo doc --open`.