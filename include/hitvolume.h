#ifndef HITVOLUME_H
#define HITVOLUME_H

// Body volume of an enemy against a ray that flies at a fixed height (the sniper beam).
// The stylus is read on screen, so "pointer on the sprite" must mean "hit": the test is made in
// screen space, with an ellipse that matches the 40x40 sprites (opaque box measured with
// tests/test_sniper_hit_volume.py: about 30 px wide, 6 px under to 33 px over the feet anchor).
// Integer maths only. The ground ellipse (ENEMY_HIT_RADIUS, 11 x 5.5 px) stays for pellets and blasts.
#define BODY_HIT_CY 14     // height of the ellipse centre over the feet, px
#define BODY_HIT_RX 15     // half width, px
#define BODY_HIT_RY 18     // half height, px

// dx = ray x - enemy x; dy = ray ground y - enemy y; h = height of the ray over the ground.
static inline int body_hit_test(int dx, int dy, int h) {
    int sy = dy - h + BODY_HIT_CY;      // ray point on screen, relative to the ellipse centre
    return dx * dx * (BODY_HIT_RY * BODY_HIT_RY) + sy * sy * (BODY_HIT_RX * BODY_HIT_RX)
        <= (BODY_HIT_RX * BODY_HIT_RX) * (BODY_HIT_RY * BODY_HIT_RY);
}

#endif
