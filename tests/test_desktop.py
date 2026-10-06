"""Exercise actual native widgets, hit testing and undo, not a browser shell."""

import math
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog, QMessageBox
from bim.app import MainWindow
from bim.model import Document


@pytest.fixture
def window(app):
    w = MainWindow()
    w.show()
    app.processEvents()
    QTest.qWait(100)
    yield w
    w.undo.setClean()
    w.close()
    app.processEvents()


def test_native_render_selection_and_measurement(window, app, tmp_path):
    v = window.viewport
    app.processEvents()
    assert len(v.drawn) > 40
    # Pick the center of the frontmost rendered face. Actual Qt mouse events perform hit testing.
    polygon, element, points = v.drawn[-1]
    center = polygon.boundingRect().center().toPoint()
    QTest.mouseClick(v, Qt.LeftButton, pos=center)
    app.processEvents()
    assert window.selected_id is not None
    assert window.name.text() == window.element().name
    window.measure_action.trigger()
    app.processEvents()
    polygon, element, points = v.drawn[-1]
    a, b = polygon[0].toPoint(), polygon[1].toPoint()
    center = polygon.boundingRect().center().toPoint()
    # Slightly inset corners keep clicks inside the filled polygon.
    p1 = QPoint(
        round(a.x() * 0.9 + center.x() * 0.1), round(a.y() * 0.9 + center.y() * 0.1)
    )
    p2 = QPoint(
        round(b.x() * 0.9 + center.x() * 0.1), round(b.y() * 0.9 + center.y() * 0.1)
    )
    QTest.mouseClick(v, Qt.LeftButton, pos=p1)
    QTest.mouseClick(v, Qt.LeftButton, pos=p2)
    app.processEvents()
    assert len(v.measure_points) == 2
    assert "distance" in window.statusBar().currentMessage()
    image = v.grab().toImage()
    assert image.width() > 500
    assert not image.isNull()
    assert v.grab().save(str(tmp_path / "viewport.png"), "PNG")
    assert (tmp_path / "viewport.png").stat().st_size > 10000


def test_edit_duplicate_delete_undo_redo(window, app):
    e = window.document.elements[2]
    window.select(e.id)
    width = e.size[0]
    window.fields[("size", 0)].setValue(width + 1.5)
    QTest.mouseClick(window.apply_button, Qt.LeftButton)
    app.processEvents()
    assert window.element().size[0] == pytest.approx(width + 1.5)
    assert not window.undo.isClean()
    window.undo.undo()
    assert window.element().size[0] == width
    window.undo.redo()
    assert window.element().size[0] == pytest.approx(width + 1.5)
    count = len(window.document.elements)
    window.duplicate()
    assert len(window.document.elements) == count + 1
    window.delete()
    assert len(window.document.elements) == count
    window.undo.undo()
    assert len(window.document.elements) == count + 1
    window.undo.redo()
    assert len(window.document.elements) == count


def test_visibility_search_floor_and_section(window, app):
    e = window.document.elements[3]
    window.select(e.id)
    item = window.items[e.id]
    item.setCheckState(1, Qt.Unchecked)
    app.processEvents()
    assert not window.element().visible
    assert all(row[1].id != e.id for row in window.viewport.world_faces())
    window.undo.undo()
    assert window.element().visible
    window.search.setText("window frame")
    assert all(
        item.isHidden() or "window frame" in item.text(0).lower()
        for item in window.items.values()
    )
    window.search.clear()
    window.floor.setCurrentIndex(window.floor.findData(1))
    app.processEvents()
    assert all(row[1].floor == 1 for row in window.viewport.world_faces())
    window.section_action.trigger()
    window.section_height.setValue(4)
    assert all(
        p[2] <= 4.000001 for row in window.viewport.world_faces() for p in row[2]
    )
    window.explode_action.trigger()
    assert window.viewport.explode == 1.5
    window.wire_action.trigger()
    assert window.viewport.mode == "wire"


def test_save_load_export_and_unsaved_cancel(window, app, tmp_path, monkeypatch):
    window.add_element("gable")
    path = tmp_path / "native.bim.json"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(path), "")
    )
    assert window.save_as()
    assert window.undo.isClean()
    count = len(window.document.elements)
    window.add_element("box")
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Cancel
    )
    assert not window.confirm_discard()
    window.undo.setClean()
    assert window.load_path(path)
    assert len(window.document.elements) == count
    obj = tmp_path / "mesh.obj"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(obj), "")
    )
    window.export_obj()
    assert obj.stat().st_size > 1000
    png = tmp_path / "view.png"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(png), "")
    )
    window.export_png()
    assert png.stat().st_size > 10000


def test_three_scene_switches_and_camera_views(window, app):
    for index in [1, 2, 0]:
        window.scene_picker.setCurrentIndex(index)
        app.processEvents()
        assert window.document.name == window.scene_picker.currentText()
        assert window.undo.isClean()
        assert window.viewport.drawn
    window.camera("top")
    assert window.viewport.elevation == math.pi / 2
    window.camera("front")
    assert window.viewport.elevation < 0.02
    window.camera("iso")
    assert 0.5 < window.viewport.elevation < 0.6
