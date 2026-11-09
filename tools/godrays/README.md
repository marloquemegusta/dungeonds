# God rays prototype

The `godrays` build variant enables the prototype only in strip mode. Its marea
is disabled for the whole variant so the effect can be reviewed without the
existing fade-to-black effect. The renderer still detects a visible tide line
and hides all rays on that engine; if that limit is removed later, this avoids
an OBJ semitransparency effect turning opaque inside the tide window.

The ray window is anchored every 256 absolute strip pixels, alternating walls;
`strip_shift_total_px()` is included so rebases do not move the effect in world
space. The hero starts at approximately world Y=1792 and the lower-screen
camera places its feet at Y=96. The interval ray starts at Y=1600; after about
160 UP frames the hero reaches approximately Y=1680, the ray's source row 80.
The placeholder's diagonal reaches lane X=256 near source row 80, so this
crosses it at the
hero's world X=256. The scenario's crossing capture is named for this geometry.

Generate and build from the worktree root:

```powershell
python tools/godrays/make_placeholder_ray.py
python tools/godrays/convert_rays.py assets/sprites/godrays/placeholder/ray_placeholder.png -o source/godrays_gfx.c
& 'C:\codexlocal\skills\agentic-ds-dev\scripts\build-project.ps1' -ProjectPath 'C:\codexlocal\dungeonds\.worktrees\proto-godrays' -Variant godrays
```

Replace the placeholder input with `assets/sprites/godrays/ray_*.png` when the
art images are ready. The converter omits fully transparent 64x64 blocks and
checks the complete tileset against bank I's 16 KiB capacity.
