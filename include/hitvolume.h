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

#define CHARGER_BODY_HIT_CY 21  // 1.5x for 60x60 charger sprite
#define CHARGER_BODY_HIT_RX 23
#define CHARGER_BODY_HIT_RY 27

#define OJO_BODY_HIT_CY 17     // Ojo rendered at 140%: ellipse follows the enlarged body and extended arm
#define OJO_BODY_HIT_RX 18
#define OJO_BODY_HIT_RY 22

// dx = ray x - enemy x; dy = ray ground y - enemy y; h = height of the ray over the ground.
static inline int body_hit_test_ex(int dx, int dy, int h, int cy, int rx, int ry) {
    int sy = dy - h + cy;               // ray point on screen, relative to the ellipse centre
    return dx * dx * (ry * ry) + sy * sy * (rx * rx)
        <= (rx * rx) * (ry * ry);
}

static inline int body_hit_test(int dx, int dy, int h) {
    return body_hit_test_ex(dx, dy, h, BODY_HIT_CY, BODY_HIT_RX, BODY_HIT_RY);
}

#endif
