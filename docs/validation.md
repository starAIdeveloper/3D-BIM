# Executed validation

Implementation environment: Python 3.12, PySide6 6.10.1, NumPy 2.2.6, Linux, native Qt offscreen platform. Date: 2026-10-06.

- 23 tests passed: project schema rejection, three scene round trips, rotation and volume, clipping, distance, OBJ indices, safe save behavior, depth-buffer occlusion, wireframe pick buffers, and actual native-widget workflows.
- Native UI workflows cover clicking rendered geometry, vertex measurement, dimension edits, duplicate/delete, undo/redo, visibility checkboxes, object search, floor filter, section/explosion/wireframe controls, project save/load, OBJ/PNG exports, unsaved-change cancellation and scene/camera switching.
- Native window screenshots captured for all three scenes through the installed desktop entry point.
- Code formatting checked with Black.

A crash caused by rebuilding the tree inside its own `itemChanged` event was fixed by deferring the rebuild. Tests reproduce visibility changes and pass. A painter-order occlusion problem was replaced with a per-pixel Z-buffer and tested with both near/far submission orders.

These are real Qt widget tests in an offscreen Linux environment, not a mocked or browser-only UI. Manual Windows/macOS hardware testing, packaged executable builds, signing and installer validation are not claimed. The supplied Windows GitHub Actions build is configured, but its execution is not represented as completed here.
