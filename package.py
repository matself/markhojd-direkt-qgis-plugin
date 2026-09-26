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


# plugins.xml för installation via "Hantera och installera insticksmoduler > Inställningar > Lägg till"
import configparser
from xml.sax.saxutils import escape

meta = configparser.ConfigParser(interpolation=None)
meta.read(root / "markhojd_direkt" / "metadata.txt", encoding="utf-8")
m = meta["general"]
repo = m["repository"].rstrip("/")
url = f"{repo}/releases/download/v{m['version']}/markhojd_direkt.zip"
xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<plugins>
  <pyqgis_plugin name="{escape(m['name'])}" version="{m['version']}">
    <description><![CDATA[{m['description']}]]></description>
    <about><![CDATA[{m['about']}]]></about>
    <version>{m['version']}</version>
    <qgis_minimum_version>{m['qgisminimumversion']}</qgis_minimum_version>
    <homepage>{escape(m['homepage'])}</homepage>
    <file_name>markhojd_direkt.zip</file_name>
    <icon>icon.svg</icon>
    <author_name><![CDATA[{m['author']}]]></author_name>
    <download_url>{url}</download_url>
    <uploaded_by><![CDATA[{m['author']}]]></uploaded_by>
    <experimental>{m['experimental']}</experimental>
    <deprecated>{m['deprecated']}</deprecated>
    <tracker>{escape(m['tracker'])}</tracker>
    <repository>{escape(repo)}</repository>
    <tags>{escape(m['tags'])}</tags>
    <server>False</server>
  </pyqgis_plugin>
</plugins>
"""
(root / "plugins.xml").write_text(xml, encoding="utf-8")
print(root / "plugins.xml")
