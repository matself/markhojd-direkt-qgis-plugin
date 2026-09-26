"""Bygger dist/markhojd_direkt.zip som kan installeras via Plugins > Install from ZIP."""
import pathlib
import zipfile

root = pathlib.Path(__file__).parent
out = root / "dist"
out.mkdir(exist_ok=True)
with zipfile.ZipFile(out / "markhojd_direkt.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in (root / "markhojd_direkt").rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts:
            z.write(f, f.relative_to(root))
    z.write(root / "LICENSE", "markhojd_direkt/LICENSE")  # licensen ska följa med i paketet
print(out / "markhojd_direkt.zip")
