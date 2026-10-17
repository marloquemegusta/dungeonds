import sys, glob, os, json
from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = Path(r"c:\codexlocal\dungeonds")
sys.path.insert(0, str(HERE))
import compare_labs as c

models = {
    "charger_run": ROOT / "assets/characters/charger/Run.fbx",
    "mario": ROOT / "assets/characters/custom/mario_camisa_blanca.fbx",
    "henar": ROOT / "assets/characters/custom/henar_top_kaki.fbx",
    "wizard": ROOT / "assets/characters/custom/wizard.fbx",
    "necron": ROOT / "assets/characters/necron/tripo_convert_c240e498-85d5-4ccc-a624-798965993caa.fbx",
}

html = (HERE / "FBX-Web-Renderer-offline.html").resolve().as_uri()
exe = sorted(glob.glob(os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-*\*\chrome-headless-shell.exe")))[-1]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=exe, args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    for name, path in models.items():
        if not path.exists():
            print(f"Skipping {name}, path not found: {path}")
            continue
        print(f"\n=================== TESTING {name} ===================")
        page.goto(html)
        page.wait_for_function("$.renderer && !$.renderer.getContext().isContextLost()", timeout=60000)
        page.set_input_files("#fbxInput", str(path))
        page.wait_for_function("!document.getElementById('btnRender').disabled", timeout=60000)
        
        # Diagnostics from loaded state
        diag = page.evaluate("""() => {
            const m = $.model;
            const r = $.modelRoot;
            const box = new hr().setFromObject(m);
            const boxR = new hr().setFromObject(r);
            const c = new K(); box.getCenter(c);
            const s = new K(); box.getSize(s);
            const cr = new K(); boxR.getCenter(cr);
            const sr = new K(); boxR.getSize(sr);
            
            // Check bones / root
            let rootBone = null;
            let hipsBone = null;
            m.traverse(n => {
                if (n.isBone) {
                    if (!rootBone) rootBone = n.name;
                    if (/hip/i.test(n.name)) hipsBone = n.name;
                }
            });
            function dump(node, depth = 0) {
                if (depth > 3) return { name: node.name, type: node.type };
                return {
                    name: node.name,
                    type: node.type,
                    pos: node.position.toArray(),
                    rot: [node.rotation.x, node.rotation.y, node.rotation.z],
                    scale: node.scale.toArray(),
                    children: (node.children || []).map(c => dump(c, depth + 1))
                };
            }
            return {
                modelPos: m.position.toArray(),
                modelScale: m.scale.toArray(),
                rootPos: r.position.toArray(),
                rootScale: r.scale.toArray(),
                boxCenter: c.toArray(),
                boxSize: s.toArray(),
                rootBoxCenter: cr.toArray(),
                rootBoxSize: sr.toArray(),
                clips: ($.clips || []).map(c => ({ name: c.name, duration: c.duration, tracks: c.tracks.length })),
                rootBone, hipsBone,
                tree: dump(r)
            };
        }""")
        print("Model diagnostics:", json.dumps(diag, indent=2))
        
        page.click("#btnRender")
        page.wait_for_function("!document.getElementById('btnRender').disabled", timeout=120000)
        
        fit = page.evaluate("window.__spriteLab.lastFit")
        print("Last fit:", json.dumps(fit, indent=2))
        
        # Analyze centroids of rendered frames
        centroids = page.evaluate("""() => {
            const frames = window.__spriteLab.frames;
            const size = parseInt(_p.resolution.value, 10);
            const count = parseInt(_p.frameCount.value, 10);
            const dirs = Ff;
            const res = [];
            for (let d = 0; d < dirs.length; d++) {
                // look at first frame of each dir
                const f = frames[d * count];
                let sumX = 0, sumY = 0, countP = 0;
                let minX = 999, maxX = -1, minY = 999, maxY = -1;
                for (let y = 0; y < size; y++) {
                    for (let x = 0; x < size; x++) {
                        const idx = (y * size + x) * 4;
                        if (f.pixels[idx + 3] > 20) {
                            sumX += x; sumY += y; countP++;
                            if (x < minX) minX = x; if (x > maxX) maxX = x;
                            if (y < minY) minY = y; if (y > maxY) maxY = y;
                        }
                    }
                }
                res.push({
                    dir: dirs[d],
                    pixels: countP,
                    cx: countP ? +(sumX / countP).toFixed(2) : null,
                    cy: countP ? +(sumY / countP).toFixed(2) : null,
                    w: countP ? maxX - minX + 1 : 0,
                    h: countP ? maxY - minY + 1 : 0,
                    minX, maxX, minY, maxY
                });
            }
            return res;
        }""")
        print(f"Centroids for {name} (size 48, target center ~23.5):")
        for row in centroids:
            print(f"  Dir {row['dir']:2s}: cx={row['cx']}, cy={row['cy']}, w={row['w']}, h={row['h']}, rangeX=[{row['minX']},{row['maxX']}]")
            
    browser.close()
