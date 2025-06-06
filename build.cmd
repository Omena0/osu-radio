
py -m nuitka --standalone --onefile --enable-plugin=tk-inter^
 --product-name="osu!radio (lazer)" --product-version=1.0.0^
 --file-description="osu!radio but for lazer."^
 --copyright="Copyright © 2025 Omena0. All rights reserved."^
 --output-dir="build"^
 --include-package-data="customtkinter"^
 --deployment --python-flag="-OO" --python-flag="-S"^
 --output-filename="osu!radio (lazer).exe"^
 src/main.py

move "build/osu!radio (lazer).exe" "dist/osu!radio (lazer).exe"
