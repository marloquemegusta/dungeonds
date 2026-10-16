#!/usr/bin/env python3
"""Embed the readable parity layer into the standalone FBX renderer."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "FBX-Web-Renderer-offline.html"
EXTENSION = HERE / "FBX-Web-Renderer-parity.js"
START = "/* SPRITE-LAB-PARITY:START */"
END = "/* SPRITE-LAB-PARITY:END */"


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    source = EXTENSION.read_text(encoding="utf-8")
    block = f"{START}\n{source}\n{END}"
    for old_start, old_end in ((START, END), ("<!-- SPRITE-LAB-PARITY:START -->", "<!-- SPRITE-LAB-PARITY:END -->")):
        if old_start in html and old_end in html:
            before, rest = html.split(old_start, 1)
            _, after = rest.split(old_end, 1)
            html = before + after
    if html.count("</script>") < 1:
        raise SystemExit("Expected a closing inline script")
    insertion = html.rfind("</script>")
    html = html[:insertion] + block + "\n" + html[insertion:]
    HTML.write_text(html, encoding="utf-8")
    print(f"Embedded {EXTENSION.name} into {HTML.name}")


if __name__ == "__main__":
    main()
