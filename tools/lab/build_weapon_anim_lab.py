#!/usr/bin/env python3
"""Build the standalone 100% Web Offline FBX Weapon & Animation Assembler Lab."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDERER_HTML = HERE / "FBX-Web-Renderer-offline.html"
UI_TEMPLATE = HERE / "weapon_anim_lab_ui.html"
OUT_HTML = HERE / "FBX-Weapon-Anim-Lab-offline.html"

MODULES = [
    "glb_loader_minimal.js",
    "fbx_binary_splicer.js",
    "retarget_and_ik_engine.js",
    "seed_catalog_data.js",
    "weapon_anim_lab_app.js",
]


def extract_three_bundle() -> str:
    html = RENDERER_HTML.read_text(encoding="utf-8")
    start = html.rfind("<script>")
    end = html.rfind("</script>")
    if start < 0 or end < 0:
        raise RuntimeError("Could not find inline script in FBX-Web-Renderer-offline.html")
    script = html[start + len("<script>") : end]
    marker = "var tp=8"
    idx = script.find(marker)
    if idx < 0:
        raise RuntimeError("Could not find 'var tp=8' boundary in FBX-Web-Renderer-offline.html")
    return script[:idx]


def main() -> None:
    ui = UI_TEMPLATE.read_text(encoding="utf-8")
    three_lib = extract_three_bundle()

    parts = [
        "<script>",
        "try {",
        "/* === 1. THREE.JS + FBXLOADER + ORBITCONTROLS + JSZIP + FFLATE CORE === */",
        three_lib,
    ]

    for mod_name in MODULES:
        mod_path = HERE / mod_name
        mod_code = mod_path.read_text(encoding="utf-8")
        parts.append(f"\n/* === MODULE: {mod_name} === */\n")
        parts.append(mod_code)

    parts.append(
        """
} catch (err) {
  console.error('Fatal Lab Bundle Error:', err);
  const banner = document.createElement('div');
  banner.style = 'position:fixed;top:0;left:0;right:0;background:#b00;color:#fff;padding:12px;z-index:99999;font-family:monospace;font-size:12px;white-space:pre-wrap;';
  banner.textContent = 'ERROR DE INICIALIZACIÓN:\\n' + (err && (err.stack || err.message || err));
  document.body.appendChild(banner);
}
</script>"""
    )

    full_script = "\n".join(parts)
    if "<!-- LAB-BUNDLE-INJECT -->" not in ui:
        raise RuntimeError("Missing <!-- LAB-BUNDLE-INJECT --> placeholder in weapon_anim_lab_ui.html")

    out_content = ui.replace("<!-- LAB-BUNDLE-INJECT -->", full_script)
    OUT_HTML.write_text(out_content, encoding="utf-8")
    size_mb = OUT_HTML.stat().st_size / (1024 * 1024)
    print(f"Built {OUT_HTML.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
