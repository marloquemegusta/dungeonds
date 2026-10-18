#ifndef LOS_H
#define LOS_H

#include <stdint.h>
#include <stdbool.h>

/**
 * Line-of-sight check using 2D Bresenham raycasting over g_dungeon_collision.
 * Solid blocking wall is collision flag == 3.
 *
 * @param px0 Starting X coordinate in world pixels.
 * @param py0 Starting Y coordinate in world pixels.
 * @param px1 Target X coordinate in world pixels.
 * @param py1 Target Y coordinate in world pixels.
 * @param max_radius_px Maximum distance in pixels allowed. If <= 0, distance is unconstrained.
 * @return 1 if line of sight is clear, 0 if blocked or out of range.
 */
int los_has_line_of_sight(int px0, int py0, int px1, int py1, int max_radius_px);

#endif // LOS_H
