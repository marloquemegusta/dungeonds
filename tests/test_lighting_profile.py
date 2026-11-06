"""The shared dungeon lighting profile (DESIGN.md 6) drives map and character renders alike."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "assets/lighting/dungeon_lighting.json"
LAB = ROOT / "tools/lab"


class LightingProfileTest(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads(PROFILE.read_text(encoding="utf-8"))

    def test_profile_fields(self):
        p = self.profile
        for light in ("key", "fill", "rim"):
            self.assertIn("intensity", p[light])
            self.assertIn("azimuthFromCamera", p[light])
            self.assertIn("elevation", p[light])
        self.assertLess(p["ambient"]["intensity"], 0.15, "ambient must stay very low")
        self.assertGreater(p["key"]["intensity"], p["fill"]["intensity"])
        self.assertGreater(p["rim"]["edge"]["intensity"], 0)
        # the rim sits behind the subject relative to the camera and is elevated
        self.assertGreaterEqual(abs(p["rim"]["azimuthFromCamera"]), 120)
        self.assertGreater(p["rim"]["elevation"], 0)
        for k in ("contrast", "saturation", "brightness"):
            self.assertGreater(p["grade"][k], 0)

    def test_offline_lab_embeds_current_profile(self):
        html = (LAB / "FBX-Web-Renderer-offline.html").read_text(encoding="utf-8")
        m = re.search(r"/\*LIGHTING_PROFILE:START\*/(.*?)/\*LIGHTING_PROFILE:END\*/", html, re.S)
        self.assertIsNotNone(m, "run python tools/lab/build_offline_renderer.py")
        self.assertEqual(json.loads(m.group(1)), self.profile)

    def test_exporters_use_profile(self):
        mapjs = (LAB / "export_map_package_headless.cjs").read_text(encoding="utf-8")
        self.assertIn("dungeon_lighting.json", mapjs)
        self.assertIn("shadowExtent", mapjs)
        self.assertIn("shadowMapSize", mapjs)
        chars = (ROOT / "tools/render_all_40px_headless.cjs").read_text(encoding="utf-8")
        self.assertIn("dungeon_lighting.json", chars)
        self.assertIn("setLightingProfile", chars)

    def test_character_settings_record_profile(self):
        for name in ("marine", "charger", "necron"):
            s = json.loads((ROOT / f"assets/sprites/characters/{name}/settings.json").read_text(encoding="utf-8"))
            self.assertEqual(s.get("lightingProfile"), self.profile["name"], name)


if __name__ == "__main__":
    unittest.main()
