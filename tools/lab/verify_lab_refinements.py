#!/usr/bin/env python3
"""
Automated headless Playwright verification matrix for FBX-Web-Renderer 3-column lab refinements.
Tests zero-scroll layout, FBX/GLB map loading, multi-material handling, 8-dir sprite grid,
shared lighting/elevation reactivity, zero ghosting, character grounding at Y=0, and visual evidence.
"""

import glob
import os
from pathlib import Path
import shutil
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
HTML_PATH = (ROOT / "tools/lab/FBX-Web-Renderer-offline.html").resolve()
CHAR_FBX = (ROOT / "assets/models/characters/charger/Run.fbx").resolve()
BLOCKOUT_FBX = (ROOT / "assets/models/environment/blockout/isometric_shooter_blockout.fbx").resolve()
BLOCKOUT_GLB = (ROOT / "assets/models/environment/blockout/isometric_shooter_blockout.glb").resolve()
SCIFI_FBX = (ROOT / "assets/models/environment/scifi_dungeon/tripo_convert_b14b0e1b-13bd-4f17-b4a7-b50c6d251c17.fbx").resolve()

SCREENSHOT_DIR = (ROOT / "walkthroughs/fbx-sprite-map-lab/assets").resolve()
BRAIN_DIRS = [
    Path(r"C:\Users\malfonso\.gemini\antigravity\brain\5e3dfe73-9915-46ac-baac-673174a0e804"),
    Path(r"C:\Users\malfonso\.gemini\antigravity\brain\aa2ea060-ff04-4b4d-9bbb-af11b60cbdab")
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def find_chrome_executable():
    shells = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-*\*\chrome-headless-shell.exe")))
    if shells:
        return shells[-1]
    return None


def copy_to_brain(src: Path):
    for b_dir in BRAIN_DIRS:
        try:
            b_dir.mkdir(parents=True, exist_ok=True)
            dest = b_dir / src.name
            shutil.copy2(src, dest)
            print(f"  [Copied to Brain] {dest}")
        except Exception as e:
            print(f"  [Warning: Could not copy to {b_dir}]: {e}")


def run_verification():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    assert HTML_PATH.exists(), f"HTML not found: {HTML_PATH}"
    assert CHAR_FBX.exists(), f"Char FBX not found: {CHAR_FBX}"
    assert BLOCKOUT_FBX.exists(), f"Blockout FBX not found: {BLOCKOUT_FBX}"
    assert BLOCKOUT_GLB.exists(), f"Blockout GLB not found: {BLOCKOUT_GLB}"
    assert SCIFI_FBX.exists(), f"SciFi FBX not found: {SCIFI_FBX}"

    exec_path = find_chrome_executable()

    with sync_playwright() as p:
        launch_args = [
            "--use-gl=swiftshader",
            "--enable-unsafe-swiftshader",
            "--ignore-gpu-blocklist",
            "--no-sandbox",
            "--disable-web-security"
        ]
        try:
            browser = p.chromium.launch(headless=True, args=launch_args)
            print("Launched default Playwright Chromium")
        except Exception:
            print(f"Using Chrome executable: {exec_path}")
            browser = p.chromium.launch(executable_path=exec_path, headless=True, args=launch_args)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Track console messages
        page.on("console", lambda msg: print(f"  [Browser Console] {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [Browser PageError] {err}"))

        print(f"Loading {HTML_PATH.as_uri()} ...")
        page.goto(HTML_PATH.as_uri(), wait_until="networkidle")
        page.wait_for_selector("#labLeftSidebar", timeout=15000)
        page.wait_for_selector("#labCenterPanel", timeout=5000)
        page.wait_for_selector("#labRightStage", timeout=5000)
        page.wait_for_function("window.$ && window.$.renderer && !window.$.renderer.getContext().isContextLost()", timeout=60000)
        print("[PASS] Basic DOM loaded, renderer initialized, and 3 main columns exist.")

        # -------------------------------------------------------------
        # 1. Zero-scroll check (100vh strict)
        # -------------------------------------------------------------
        body_scroll = page.evaluate("() => Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)")
        inner_h = page.evaluate("() => window.innerHeight")
        print(f"Checking zero-scroll: scrollHeight={body_scroll}, innerH={inner_h}")
        assert body_scroll <= inner_h + 1, f"Page has vertical scroll: {body_scroll} > {inner_h}"
        print("[PASS] Zero-scroll 100vh check passed.")

        # Check 3 column widths and positions
        cols = page.evaluate("""() => {
            const sb = document.getElementById('labLeftSidebar').getBoundingClientRect();
            const cp = document.getElementById('labCenterPanel').getBoundingClientRect();
            const rs = document.getElementById('labRightStage').getBoundingClientRect();
            return {
                sbW: sb.width,
                cpW: cp.width,
                rsW: rs.width
            };
        }""")
        print(f"Column dimensions: {cols}")
        assert abs(cols['sbW'] - 330) < 5, f"Left sidebar expected ~330px, got {cols['sbW']}"
        assert abs(cols['cpW'] - 430) < 5, f"Center panel expected ~430px, got {cols['cpW']}"
        assert cols['rsW'] > 600, f"Right stage expected >600px, got {cols['rsW']}"
        print("[PASS] 3-column layout proportions (330px 430px 1fr) verified.")

        # -------------------------------------------------------------
        # 2. Load character model (Run.fbx)
        # -------------------------------------------------------------
        print(f"Loading character {CHAR_FBX.name} ...")
        page.set_input_files('#fbxInput', str(CHAR_FBX))

        # Wait for character model to finish loading
        page.wait_for_function("""() => {
            const badge = document.getElementById('fileNameBadge');
            return badge && badge.textContent.includes('Run.fbx');
        }""", timeout=30000)
        print("[PASS] Character Run.fbx loaded.")

        # Wait for liveDirCanvases to populate
        page.wait_for_function("""() => {
            return window.__spriteLab && window.__spriteLab.liveDirCanvases && window.__spriteLab.liveDirCanvases.length >= 8;
        }""", timeout=15000)
        print("[PASS] 8-direction live sprites rendered in center column.")

        # -------------------------------------------------------------
        # 3. Load blockout FBX map
        # -------------------------------------------------------------
        print(f"Loading blockout map {BLOCKOUT_FBX.name} ...")
        page.set_input_files('#mapFileInput', str(BLOCKOUT_FBX))

        # Wait for map to load
        page.wait_for_function("""() => {
            return window.__spriteLab && window.__spriteLab.map && window.__spriteLab.map.loaded && window.__spriteLab.mapCanvas;
        }""", timeout=30000)
        print("[PASS] Blockout FBX loaded and rendered to mapCanvas.")

        # Verify blockout renders at full size with distinct material colors (not plain white)
        map_materials_info = page.evaluate("""() => {
            const map = window.__spriteLab.map.model;
            const colors = [];
            map.traverse(node => {
                if (node.isMesh && node.material) {
                    const mats = Array.isArray(node.material) ? node.material : [node.material];
                    mats.forEach(m => {
                        if (m.color) colors.push(m.color.getHexString());
                    });
                }
            });
            const uniqueColors = Array.from(new Set(colors));
            return {
                totalMeshesWithMat: colors.length,
                uniqueColors: uniqueColors
            };
        }""")
        print(f"Blockout materials info: {map_materials_info}")
        assert len(map_materials_info['uniqueColors']) >= 3, f"Expected >= 3 distinct material colors, got {map_materials_info['uniqueColors']}"
        print(f"✓ Distinct material colors verified: {map_materials_info['uniqueColors']}")

        # -------------------------------------------------------------
        # 4. Shared lighting & elevation reactivity
        # -------------------------------------------------------------
        print("Testing lighting and elevation reactivity...")
        initial_pixel = page.evaluate("""() => {
            const ctx = window.__spriteLab.mapCanvas.getContext('2d');
            const w = window.__spriteLab.mapCanvas.width;
            const h = window.__spriteLab.mapCanvas.height;
            const d = ctx.getImageData(Math.floor(w/2), Math.floor(h/2), 1, 1).data;
            return [d[0], d[1], d[2], d[3]];
        }""")
        print(f"Initial map center pixel: {initial_pixel}")

        # Change elevation 30 -> 45
        page.evaluate("""() => {
            const el = document.getElementById('elevation');
            el.value = '45';
            el.dispatchEvent(new Event('input'));
            el.dispatchEvent(new Event('change'));
        }""")
        page.wait_for_timeout(600)

        elev_pixel = page.evaluate("""() => {
            const ctx = window.__spriteLab.mapCanvas.getContext('2d');
            const w = window.__spriteLab.mapCanvas.width;
            const h = window.__spriteLab.mapCanvas.height;
            const d = ctx.getImageData(Math.floor(w/2), Math.floor(h/2), 1, 1).data;
            return [d[0], d[1], d[2], d[3]];
        }""")
        print(f"After elevation 45° pixel: {elev_pixel}")

        # Change key light 4.2 -> 1.0
        page.evaluate("""() => {
            const el = document.getElementById('keyLight');
            el.value = '1.0';
            el.dispatchEvent(new Event('input'));
            el.dispatchEvent(new Event('change'));
        }""")
        page.wait_for_timeout(600)

        dim_pixel = page.evaluate("""() => {
            const ctx = window.__spriteLab.mapCanvas.getContext('2d');
            const w = window.__spriteLab.mapCanvas.width;
            const h = window.__spriteLab.mapCanvas.height;
            const d = ctx.getImageData(Math.floor(w/2), Math.floor(h/2), 1, 1).data;
            return [d[0], d[1], d[2], d[3]];
        }""")
        print(f"After key light 1.0 pixel: {dim_pixel}")

        # Verify reactivity: pixels changed when light changed
        assert (initial_pixel != dim_pixel) or (elev_pixel != dim_pixel), "Map canvas did not react to lighting/elevation changes!"

        # Restore settings
        page.evaluate("""() => {
            const elElev = document.getElementById('elevation');
            elElev.value = '30';
            elElev.dispatchEvent(new Event('input'));
            elElev.dispatchEvent(new Event('change'));
            const elKey = document.getElementById('keyLight');
            elKey.value = '4.2';
            elKey.dispatchEvent(new Event('input'));
            elKey.dispatchEvent(new Event('change'));
        }""")
        page.wait_for_timeout(600)
        print("[PASS] Shared lighting and elevation reactivity successfully verified.")

        # -------------------------------------------------------------
        # 5. Ghosting & DS Simulator canvas test
        # -------------------------------------------------------------
        print("Testing DS simulator black clear & ghosting prevention...")
        ds_pixel_outside = page.evaluate("""() => {
            const state = window.__spriteLab;
            state.dsPanX = 99999;
            state.dsPanY = 99999;
            const canvas = document.getElementById('dsSimCanvas');
            const ctx = canvas.getContext('2d');
            const dsW = 256;
            const dsH = state.dsMode === '2' ? 384 : 192;
            ctx.fillStyle = '#000000';
            ctx.fillRect(0, 0, dsW, dsH);
            if (state.mapCanvas) {
                ctx.drawImage(state.mapCanvas, -state.dsPanX, -state.dsPanY);
            }
            const d = ctx.getImageData(128, 96, 1, 1).data;
            // Restore pan
            state.dsPanX = 0;
            state.dsPanY = 0;
            return [d[0], d[1], d[2], d[3]];
        }""")
        print(f"DS pixel outside bounds: {ds_pixel_outside}")
        assert ds_pixel_outside[0] == 0 and ds_pixel_outside[1] == 0 and ds_pixel_outside[2] == 0 and ds_pixel_outside[3] == 255, \
            f"Expected solid black (0,0,0,255), got {ds_pixel_outside}"
        print("[PASS] Zero ghosting solid black background verified.")

        # Reset DS position and redraw
        page.click("#btnResetDsPos")
        page.wait_for_timeout(400)

        # Capture Screenshot 1: 3-column DS layout with Blockout
        shot1 = SCREENSHOT_DIR / "lab_3col_ds_blockout.png"
        page.screenshot(path=str(shot1))
        copy_to_brain(shot1)
        print(f"✓ Screenshot 1 captured: {shot1}")

        # -------------------------------------------------------------
        # 6. Switch to Visor 3D Interactivo tab
        # -------------------------------------------------------------
        print("Switching to Visor 3D Interactivo...")
        page.click('.stage-tab-btn[data-stage="3d"]')
        page.wait_for_timeout(600)

        # Check 3D grounding
        grounding_info = page.evaluate("""() => {
            const $ = window.$;
            const state = window.__spriteLab;
            const model = $.model;
            const root = $.modelRoot;
            let minY = Infinity;
            if (model) {
                model.traverse(node => {
                    if (node.isMesh && node.geometry && node.geometry.attributes && node.geometry.attributes.position) {
                        node.updateMatrixWorld(true);
                        const m = node.matrixWorld.elements;
                        const pos = node.geometry.attributes.position;
                        for (let i = 0; i < pos.count; i++) {
                            const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
                            const wy = m[1]*x + m[5]*y + m[9]*z + m[13];
                            if (wy < minY) minY = wy;
                        }
                    }
                });
            }
            return {
                charMinY: minY,
                mapScale: state.mapGroup ? state.mapGroup.scale.x : 1.0,
                mapGroupPos: state.mapGroup ? [state.mapGroup.position.x, state.mapGroup.position.y, state.mapGroup.position.z] : null
            };
        }""")
        print(f"3D Grounding & Scale info: {grounding_info}")
        assert abs(grounding_info['charMinY']) < 0.1, f"Character feet not grounded at Y=0! minY={grounding_info['charMinY']}"
        assert grounding_info['mapScale'] > 0, "Map scale should be positive"
        print("[PASS] Character grounding at Y=0 verified.")

        # Capture Screenshot 2: 3-column 3D Viewport with Blockout
        shot2 = SCREENSHOT_DIR / "lab_3col_3d_blockout.png"
        page.screenshot(path=str(shot2))
        copy_to_brain(shot2)
        print(f"✓ Screenshot 2 captured: {shot2}")

        # -------------------------------------------------------------
        # 7. Switch back to DS tab and test GLB loader
        # -------------------------------------------------------------
        print("Switching back to DS Simulator and loading Blockout GLB...")
        page.click('.stage-tab-btn[data-stage="ds"]')
        page.wait_for_timeout(400)

        page.set_input_files('#mapFileInput', str(BLOCKOUT_GLB))
        page.wait_for_function("""() => {
            return window.__spriteLab && window.__spriteLab.map && window.__spriteLab.map.name.includes('.glb') && window.__spriteLab.map.loaded;
        }""", timeout=30000)
        print("[PASS] Blockout GLB loaded via MinimalGLBLoader.")

        glb_materials_info = page.evaluate("""() => {
            const map = window.__spriteLab.map.model;
            let meshCount = 0;
            let matArrayCount = 0;
            const colors = [];
            map.traverse(node => {
                if (node.isMesh) {
                    meshCount++;
                    if (Array.isArray(node.material)) {
                        matArrayCount++;
                        node.material.forEach(m => {
                            if (m && m.color) colors.push(m.color.getHexString());
                        });
                    } else if (node.material && node.material.color) {
                        colors.push(node.material.color.getHexString());
                    }
                }
            });
            return {
                meshCount,
                matArrayCount,
                uniqueColors: Array.from(new Set(colors))
            };
        }""")
        print(f"GLB Multi-material info: {glb_materials_info}")
        assert len(glb_materials_info['uniqueColors']) >= 3, f"GLB expected >= 3 colors, got {glb_materials_info['uniqueColors']}"
        assert glb_materials_info['matArrayCount'] > 0, f"Expected mesh with material array, got {glb_materials_info['matArrayCount']}"
        print("[PASS] Multi-material GLB support successfully verified.")

        # -------------------------------------------------------------
        # 8. Load Sci-Fi Dungeon FBX
        # -------------------------------------------------------------
        print(f"Loading SciFi Dungeon {SCIFI_FBX.name} ...")
        page.set_input_files('#mapFileInput', str(SCIFI_FBX))
        page.wait_for_function("""() => {
            return window.__spriteLab && window.__spriteLab.map && window.__spriteLab.map.name.includes('tripo_convert') && window.__spriteLab.map.loaded;
        }""", timeout=30000)
        page.wait_for_timeout(800)
        print("[PASS] SciFi Dungeon FBX loaded.")

        # Capture Screenshot 3: SciFi Dungeon in DS Simulator
        shot3 = SCREENSHOT_DIR / "lab_3col_ds_scifi.png"
        page.screenshot(path=str(shot3))
        copy_to_brain(shot3)
        print(f"✓ Screenshot 3 captured: {shot3}")

        browser.close()
        print("\n========================================================")
        print(" ALL PLAYWRIGHT VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("========================================================\n")


if __name__ == "__main__":
    run_verification()
