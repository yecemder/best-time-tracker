# Best Time Tracker
Imports results from Hy-Tek meet manager and converts into a CSV using terrible ideas and misuse of PDFs.

## Requirements:
Requires Pango installed for `weasyprint` library functionality.
1. Install [MSYS2](https://www.msys2.org/#installation) with the default options.
2. Execute this command in the MSYS shell: `pacman -S mingw-w64-x86_64-pango`
3. Use pip to install the following libraries with `pip install`:
   - `pypdf`
   - `requests`
   - `weasyprint`