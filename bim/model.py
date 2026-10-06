"""Metre-based parametric geometry and safe project persistence."""
from dataclasses import dataclass, asdict
from pathlib import Path
import copy
import json
import math
import os
import re
import uuid

SCHEMA_VERSION = 1

@dataclass
class Element:
    id: str
    name: str
    category: str
    floor: int
    size: list[float]
    position: list[float]
    color: str = '#d1d4d5'
    material: str = 'Concrete'
    kind: str = 'box'
    visible: bool = True
    rotation: float = 0.0

    def vertices(self):
        x, y, z = [v / 2 for v in self.size]
        if self.kind == 'gable':
            points = [(-x,-y,-z),(x,-y,-z),(0,-y,z),(-x,y,-z),(x,y,-z),(0,y,z)]
        else:
            points = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        a = math.radians(self.rotation)
        return [(self.position[0]+px*math.cos(a)-py*math.sin(a),
                 self.position[1]+px*math.sin(a)+py*math.cos(a),
                 self.position[2]+pz) for px,py,pz in points]

    def faces(self):
        return [(0,1,2),(3,5,4),(0,3,4,1),(1,4,5,2),(2,5,3,0)] if self.kind == 'gable' else [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]

    def volume(self):
        return math.prod(self.size) * (0.5 if self.kind == 'gable' else 1)

    def clone(self):
        result = copy.deepcopy(self)
        result.id = uuid.uuid4().hex
        result.name += ' copy'
        result.position[0] += 1
        return result

class Document:
    def __init__(self, name='Untitled', elements=None):
        self.name = name
        self.elements = list(elements or [])

    def to_dict(self):
        return {'schema_version': SCHEMA_VERSION, 'name': self.name, 'units': 'metres', 'elements': [asdict(e) for e in self.elements]}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get('schema_version') != SCHEMA_VERSION or data.get('units') != 'metres':
            raise ValueError('Unsupported project schema or units.')
        if not isinstance(data.get('name'), str) or len(data['name']) > 200:
            raise ValueError('Project name must be text up to 200 characters.')
        rows = data.get('elements')
        if not isinstance(rows, list) or len(rows) > 1500:
            raise ValueError('Project supports at most 1500 elements.')
        ids, elements = set(), []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Invalid element record.')
            try:
                e = Element(**row)
            except TypeError as exc:
                raise ValueError('Invalid element fields.') from exc
            for field in ('id','name','category','material'):
                if not isinstance(getattr(e,field), str) or not getattr(e,field) or len(getattr(e,field)) > 200:
                    raise ValueError('Element metadata must be nonempty text up to 200 characters.')
            if e.id in ids:
                raise ValueError('Element IDs must be unique.')
            ids.add(e.id)
            if type(e.floor) is not int or not 0 <= e.floor <= 100 or type(e.visible) is not bool or e.kind not in ('box','gable'):
                raise ValueError('Invalid storey, visibility or geometry kind.')
            for field in ('position','size'):
                values = getattr(e,field)
                if not isinstance(values,list) or len(values)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 for v in values):
                    raise ValueError('Geometry requires three finite numbers within ±10000.')
            if any(v <= 0 for v in e.size):
                raise ValueError('Dimensions must be positive.')
            if type(e.rotation) not in (int,float) or not math.isfinite(e.rotation) or abs(e.rotation)>36000:
                raise ValueError('Rotation must be finite degrees.')
            if not isinstance(e.color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',e.color):
                raise ValueError('Color must be hexadecimal.')
            elements.append(e)
        return cls(data['name'], elements)

    def save(self, path):
        path = Path(path)
        self.from_dict(self.to_dict())
        temporary = path.with_name(path.name + '.tmp')
        try:
            with temporary.open('w', encoding='utf-8') as file:
                json.dump(self.to_dict(), file, indent=2, allow_nan=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path):
        if Path(path).stat().st_size > 5*1024*1024:
            raise ValueError('Maximum project size is 5 MB.')
        return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))

    def export_obj(self, path, include_hidden=False):
        lines = ['# 3D-BIM concept mesh; XYZ metres, Z up']
        offset = 1
        for e in self.elements:
            if not e.visible and not include_hidden:
                continue
            lines.append('o ' + re.sub(r'[^a-zA-Z0-9_-]', '_', e.name))
            vertices = e.vertices()
            lines += ['v ' + ' '.join(f'{v:.6f}' for v in p) for p in vertices]
            lines += ['f ' + ' '.join(str(offset+i) for i in face) for face in e.faces()]
            offset += len(vertices)
        Path(path).write_text('\n'.join(lines)+'\n', encoding='utf-8')


def clip_polygon(points, height):
    """Clip a polygon to the horizontal half-space Z <= height."""
    output = []
    for a,b in zip(points, points[1:]+points[:1]):
        inside_a, inside_b = a[2] <= height, b[2] <= height
        if inside_a:
            output.append(a)
        if inside_a != inside_b:
            t = (height-a[2])/(b[2]-a[2])
            output.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    return output


def distance(a,b):
    return math.dist(a,b)
