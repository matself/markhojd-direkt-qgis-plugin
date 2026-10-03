"""Builds dist/markhojd_direkt.<version>.zip, installable via Plugins > Install from ZIP."""
import configparser
import pathlib
import zipfile
from xml.sax.saxutils import escape

root = pathlib.Path(__file__).parent
meta = configparser.ConfigParser(interpolation=None)
meta.read(root / "markhojd_direkt" / "metadata.txt", encoding="utf-8")
m = meta["general"]
zip_name = f"markhojd_direkt.{m['version']}.zip"
out = root / "dist"
out.mkdir(exist_ok=True)
with zipfile.ZipFile(out / zip_name, "w", zipfile.ZIP_DEFLATED) as z:
    for f in (root / "markhojd_direkt").rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts:
            z.write(f, f.relative_to(root))
print(out / zip_name)


# plugins.xml for installation via Manage and Install Plugins > Settings > Add
repo = m["repository"].rstrip("/")
url = f"{repo}/releases/download/v{m['version']}/{zip_name}"
xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<plugins>
  <pyqgis_plugin name="{escape(m['name'])}" version="{m['version']}">
    <description><![CDATA[{m['description']}]]></description>
    <about><![CDATA[{m['about']}]]></about>
    <version>{m['version']}</version>
    <qgis_minimum_version>{m['qgisminimumversion']}</qgis_minimum_version>
    <homepage>{escape(m['homepage'])}</homepage>
    <file_name>{zip_name}</file_name>
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
