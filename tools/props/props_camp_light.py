"""Light geometry of the night camp (DESIGN.md 7.5): the bonfire at world ground point (128, 300) is the only
warm light. Shared by props_camp_night.py (lab key direction) and prop_shadows.py (shadow direction).

Convention: for a prop at ground (x, y), v = (x - 128, 2 * (y - 300)) is the true ground vector fire -> prop
(right, toward the viewer; the 2:1 floor stretches y). The light reaches the prop from -v.
GLB frame of the props (camera azimuth 135, elevation 30; see prop_shadows.py): screen right = (-1, 0, -1)/sqrt2,
ground toward the viewer = (+1, 0, -1)/sqrt2 in (x, y up, z)."""
import math

FIRE = (128, 300)
S2 = math.sqrt(0.5)


def fire_dir_xz(x, y, fire=FIRE):
    """Unit horizontal vector (GLB x, z) from the prop toward the fire."""
    vx, vy = x - fire[0], 2 * (y - fire[1])
    n = math.hypot(vx, vy) or 1.0
    ar, ad = -vx / n, -vy / n            # toward the fire: (screen right, toward viewer)
    return (ar * -S2 + ad * S2, ar * -S2 + ad * -S2)


def fire_distance(x, y, fire=FIRE):
    return math.hypot(x - fire[0], 2 * (y - fire[1]))


def key_pos(x, y, elevation_deg, fire=FIRE):
    """Unit vector toward a light `elevation_deg` above the horizon, in the fire's azimuth."""
    hx, hz = fire_dir_xz(x, y, fire)
    e = math.radians(elevation_deg)
    return [hx * math.cos(e), math.sin(e), hz * math.cos(e)]
