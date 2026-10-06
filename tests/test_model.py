import copy
import json
import math
import pytest
from bim.model import Document, Element, clip_polygon, distance
from bim.samples import sample


@pytest.mark.parametrize("index", [0, 1, 2])
def test_samples_validate_and_roundtrip(index, tmp_path):
    d = sample(index)
    assert len(d.elements) > 30
    path = tmp_path / "scene.bim.json"
    d.save(path)
    assert Document.load(path).to_dict() == d.to_dict()
    assert not path.with_name(path.name + ".tmp").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["elements"][0]["size"].__setitem__(0, -1),
        lambda d: d["elements"][0]["position"].__setitem__(0, float("nan")),
        lambda d: d["elements"][0].__setitem__("floor", True),
        lambda d: d["elements"][0].__setitem__("color", "red"),
        lambda d: d["elements"][0].__setitem__("rotation", float("inf")),
        lambda d: d["elements"][1].__setitem__("id", d["elements"][0]["id"]),
        lambda d: d.__setitem__("schema_version", 2),
        lambda d: d["elements"][0].__setitem__("name", ""),
    ],
)
def test_invalid_data_rejected(change):
    d = sample().to_dict()
    change(d)
    with pytest.raises(ValueError):
        Document.from_dict(d)


def test_geometry_rotation_and_volume():
    e = Element("a", "A", "Walls", 0, [2, 4, 6], [0, 0, 0])
    assert e.volume() == 48
    e.rotation = 90
    assert e.vertices()[0] == pytest.approx([2, -1, -3])
    e.kind = "gable"
    assert e.volume() == 24
    assert len(e.vertices()) == 6


def test_clip_plane_intersections_and_distance():
    points = [(0, 0, 0), (2, 0, 0), (2, 0, 4), (0, 0, 4)]
    clipped = clip_polygon(points, 2)
    assert len(clipped) == 4
    assert max(p[2] for p in clipped) == 2
    assert distance((0, 0, 0), (3, 4, 12)) == 13


def test_obj_vertex_indices_valid_and_hidden_omitted(tmp_path):
    d = sample(1)
    d.elements[0].visible = False
    path = tmp_path / "mesh.obj"
    d.export_obj(path)
    lines = path.read_text().splitlines()
    count = sum(s.startswith("v ") for s in lines)
    assert count == sum(len(e.vertices()) for e in d.elements if e.visible)
    for line in lines:
        if line.startswith("f "):
            assert all(1 <= int(i) <= count for i in line.split()[1:])


def test_save_rejects_invalid_model_without_overwriting(tmp_path):
    d = sample()
    path = tmp_path / "scene.json"
    d.save(path)
    before = path.read_bytes()
    d.elements[0].size[0] = 0
    with pytest.raises(ValueError):
        d.save(path)
    assert path.read_bytes() == before
