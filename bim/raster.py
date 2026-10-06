"""Small vectorized orthographic Z-buffer renderer for opaque concept meshes."""

import numpy as np


def rasterize(faces, project, depth, width, height, colors, wire=False):
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    zbuffer = np.full((height, width), -np.inf, dtype=np.float64)
    hit = np.full((height, width), -1, dtype=np.int32)
    for index, (_, element, points, normal) in enumerate(faces):
        p = [project(v) for v in points]
        screen = [(v.x(), v.y(), depth(world)) for v, world in zip(p, points)]
        color = colors[index]
        for k in range(1, len(screen) - 1):
            triangle = [screen[0], screen[k], screen[k + 1]]
            xmin = max(0, int(np.floor(min(v[0] for v in triangle))))
            xmax = min(width - 1, int(np.ceil(max(v[0] for v in triangle))))
            ymin = max(0, int(np.floor(min(v[1] for v in triangle))))
            ymax = min(height - 1, int(np.ceil(max(v[1] for v in triangle))))
            if xmin > xmax or ymin > ymax:
                continue
            (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = triangle
            denominator = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(denominator) < 1e-9:
                continue
            yy, xx = np.ogrid[ymin : ymax + 1, xmin : xmax + 1]
            a = (
                (y1 - y2) * (xx + 0.5 - x2) + (x2 - x1) * (yy + 0.5 - y2)
            ) / denominator
            b = (
                (y2 - y0) * (xx + 0.5 - x2) + (x0 - x2) * (yy + 0.5 - y2)
            ) / denominator
            c = 1 - a - b
            z = a * z0 + b * z1 + c * z2
            region = zbuffer[ymin : ymax + 1, xmin : xmax + 1]
            mask = (a >= -1e-8) & (b >= -1e-8) & (c >= -1e-8) & (z > region)
            region[mask] = z[mask]
            hit[ymin : ymax + 1, xmin : xmax + 1][mask] = index
            if not wire:
                pixels[ymin : ymax + 1, xmin : xmax + 1][mask] = color
    # Edges share the depth test, so furniture and walls behind the roof stay hidden.
    for index, (_, element, points, normal) in enumerate(faces):
        color = (
            [52, 127, 237, 255]
            if colors[index][0] == 135 and colors[index][1] == 181
            else [92, 101, 108, 255]
        )
        screen = [(project(v).x(), project(v).y(), depth(v)) for v in points]
        for a, b in zip(screen, screen[1:] + screen[:1]):
            count = min(10000, max(2, int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1))
            t = np.linspace(0, 1, count)
            x = np.rint(a[0] + t * (b[0] - a[0])).astype(int)
            y = np.rint(a[1] + t * (b[1] - a[1])).astype(int)
            z = a[2] + t * (b[2] - a[2])
            valid = (x >= 0) & (x < width) & (y >= 0) & (y < height)
            x = x[valid]
            y = y[valid]
            z = z[valid]
            visible = z >= zbuffer[y, x] - 0.04
            pixels[y[visible], x[visible]] = color
    return pixels, hit
