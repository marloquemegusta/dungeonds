#!/usr/bin/env python3
"""Embed the readable parity layer and GLB loader into the standalone FBX renderer."""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "FBX-Web-Renderer-offline.html"
EXTENSION = HERE / "FBX-Web-Renderer-parity.js"
GLB_LOADER = HERE / "glb_loader_minimal.js"
LIGHTING = HERE.parents[1] / "assets/lighting/dungeon_lighting.json"
START = "/* SPRITE-LAB-PARITY:START */"
END = "/* SPRITE-LAB-PARITY:END */"


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    glb_source = GLB_LOADER.read_text(encoding="utf-8") if GLB_LOADER.exists() else ""
    source = EXTENSION.read_text(encoding="utf-8")
    profile = json.dumps(json.loads(LIGHTING.read_text(encoding="utf-8")), separators=(",", ":"))
    source = re.sub(r"/\*LIGHTING_PROFILE:START\*/.*?/\*LIGHTING_PROFILE:END\*/",
                    lambda _m: f"/*LIGHTING_PROFILE:START*/{profile}/*LIGHTING_PROFILE:END*/", source, count=1, flags=re.S)
    combined = f"{glb_source}\n\n{source}" if glb_source else source
    block = f"{START}\n{combined}\n{END}"
    for old_start, old_end in ((START, END), ("<!-- SPRITE-LAB-PARITY:START -->", "<!-- SPRITE-LAB-PARITY:END -->")):
        if old_start in html and old_end in html:
            before, rest = html.split(old_start, 1)
            _, after = rest.split(old_end, 1)
            html = before + after
    if html.count("</script>") < 1:
        raise SystemExit("Expected a closing inline script")
    insertion = html.rfind("</script>")
    html = html[:insertion] + block + "\n" + html[insertion:]
    HTML.write_text(html, encoding="utf-8", newline="\n")
    print(f"Embedded {GLB_LOADER.name} and {EXTENSION.name} into {HTML.name}")


if __name__ == "__main__":
    main()
