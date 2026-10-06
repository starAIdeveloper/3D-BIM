import pytest
from PySide6.QtCore import QPointF
from bim.raster import rasterize


@pytest.mark.parametrize("reverse", [False, True])
def test_near_geometry_occludes_far_geometry_in_any_order(reverse):
    near = (0, None, [(5, 5, 8), (45, 5, 8), (45, 45, 8), (5, 45, 8)], None)
    far = (0, None, [(5, 5, 2), (45, 5, 2), (45, 45, 2), (5, 45, 2)], None)
    faces = [near, far] if reverse else [far, near]
    colors = (
        [[0, 200, 0, 255], [200, 0, 0, 255]]
        if reverse
        else [[200, 0, 0, 255], [0, 200, 0, 255]]
    )
    pixels, hit = rasterize(
        faces, lambda p: QPointF(p[0], p[1]), lambda p: p[2], 50, 50, colors
    )
    assert list(pixels[25, 25]) == [0, 200, 0, 255]
    assert hit[25, 25] == (0 if reverse else 1)
    assert hit[0, 0] == -1
    assert pixels[0, 0, 3] == 0


def test_wireframe_keeps_pickable_geometry_and_transparent_interior():
    faces = [(0, None, [(5, 5, 8), (45, 5, 8), (45, 45, 8), (5, 45, 8)], None)]
    pixels, hit = rasterize(
        faces,
        lambda p: QPointF(p[0], p[1]),
        lambda p: p[2],
        50,
        50,
        [[0, 200, 0, 255]],
        wire=True,
    )
    assert hit[25, 25] == 0
    assert pixels[25, 25, 3] == 0
    assert pixels[5, 25, 3] == 255
