# Dreadhollow — The Cursed Kingdom

300 static stylized low-poly models · Kareel Games · Version 1.0

Build haunted crypts, evil temples, cemeteries, prisons, dark laboratories, and
corrupted outdoor levels with coordinated obsidian, thorned iron, bone, crimson,
violet, and spectral-green assets.

## Start here

Open Previews/catalog.html in a browser. The searchable offline catalog shows
every asset, four actual export views, measured dimensions, triangle counts,
placement notes, and download links. No server or internet connection is needed.
For a fast import with embedded PBR materials, start with GLB.

## Included folders

- GLB: 300 models with embedded PBR textures.
- FBX: 300 models with embedded base color and emission images.
- OBJ: 300 models and 300 MTL files; preserve the adjacent Textures folder.
- Blender: 300 editable .blend masters with packed textures.
- Textures: four 512 × 512 PNG atlases: base color, ORM, emission, neutral normal.
- Previews: 1,200 actual exported-model views, catalog/review sheets, scenes,
  a full collection gallery, and the searchable HTML catalog.
- Demo: composed Blender courtyard, all-model Blender gallery, placement data,
  and a runnable Godot project (Demo/Godot/project.godot).
- Documentation: inventory, technical guide, production record, and licenses.
- QA: preserved factory validation records; see QA/README.txt for path mapping.
- Authoring: frozen procedural production project, recipe, scripts, and rebuild
  wrapper. This is optional for using or editing the delivered models.

100 architecture + 120 props/environment + 80 equipment/pickups = 300 models.
The count includes 18 explicitly declared variants; there are 282 designs when
those variants are excluded. manifest.json and ASSET_INDEX.txt list each model.

## Technical notes

Units are meters. Blender is Z-up; GLB/FBX/OBJ exports are Y-up. Every model is a
single mesh with one atlas material, applied scale, a ground placement pivot,
and one UV layer. Triangle counts range from 36 to 3,056. Standard floor tiles
span 2 × 2 m with a top at 0.22 m. Standard walls span 2 m and rise 2.4 m.
Doors, arches, fences, and landmarks have documented exceptions.

GLB contains base color, metallic/roughness, and emission. FBX/OBJ importer shader
support varies: reconnect the supplied ORM atlas as needed (R = constant 1,
G = roughness, B = metallic). The optional neutral normal map is disconnected;
facets and bevels are modeled geometry. Lighting shown in previews is not baked
into the base color. Emission does not automatically create a realtime light.

These are static props and pickups. No rigs, animations, collision meshes,
separate LOD meshes, Unity packages, or Unreal projects are supplied. Open
containers have interiors. Doors and lids share a combined mesh; separate their
parts and set hinge pivots in Blender if your game needs animation. Godot's
demo supports left-drag orbit, wheel zoom, and R to reset.

## Source and reproduction

Authoring contains the original production project and its own README.md and
Documentation folder. With Blender, Godot, and Python/Pillow installed, run the
wrapper from PowerShell and explicitly set a NEW output folder, for example:

& '.\Authoring\Rebuild Pack.ps1' -OutputDir '..\Dreadhollow_Rebuild' -PythonPath 'C:\Path\To\python.exe' -BlenderPath 'C:\Path\To\blender.exe' -GodotPath 'C:\Path\To\godot_console.exe'

The factory rebuild generates the original Models/ and Source/ directory layout,
not this flattened customer layout. The supplied exports and packed .blend
masters work directly without rebuilding or running the production code.

## Rights and production disclosure

LICENSE.txt permits commercial use in unlimited finished projects, edits, and
project-team sharing, without royalties or required credit. Standalone asset
redistribution/resale is restricted; read the full terms. Production scripts
are separately GPL-2.0-or-later; Godot demo scripts are MIT. Asset outputs are
governed by the commercial asset license, not the script license.

The models and palette were authored using Codex-assisted procedural Blender
code. Names and documentation also use AI assistance. No raster image generation,
image-to-3D system, downloaded texture, or third-party mesh was used. Store and
catalog previews show actual included model exports. Details and production
evidence are included in Documentation/PROVENANCE.md and QA.

This is a technically verified static asset edition. Technical reports do not
establish an objective AAA art certification; creator visual approval remains
an artistic decision. file_manifest.json records this customer package's hashes.
