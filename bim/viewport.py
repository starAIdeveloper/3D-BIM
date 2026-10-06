"""CPU-rendered orthographic mesh viewport with native Qt interaction."""
import math
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget
from .model import clip_polygon, distance


def normal(points):
    a,b,c=points[:3]
    u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
    n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    length=math.sqrt(sum(x*x for x in n)) or 1
    return [x/length for x in n]

class Viewport(QWidget):
    selected = Signal(str)
    measured = Signal(float)
    camera_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500,400)
        self.setMouseTracking(True)
        self.document=None
        self.selected_id=None
        self.yaw=math.radians(40)
        self.elevation=math.radians(32)
        self.scale=35.0
        self.pan=[0.,0.]
        self.center=[0.,0.,2.]
        self.last_mouse=None
        self.dragged=False
        self.floor=None
        self.section=None
        self.explode=0.
        self.mode='solid'
        self.grid=True
        self.measure=False
        self.measure_points=[]
        self.drawn=[]
        self.setObjectName('viewport')

    def fit(self):
        if not self.document or not self.document.elements:
            self.center=[0.,0.,0.];self.scale=30.;self.pan=[0.,0.];self.update();return
        vertices=[v for e in self.document.elements if e.visible for v in e.vertices()]
        if not vertices:return
        bounds=[(min(p[i] for p in vertices),max(p[i] for p in vertices)) for i in range(3)]
        self.center=[(a+b)/2 for a,b in bounds]
        self.scale=1.;self.pan=[0.,0.]
        projected=[self.project(p) for p in vertices]
        width=max(p.x() for p in projected)-min(p.x() for p in projected)
        height=max(p.y() for p in projected)-min(p.y() for p in projected)
        self.scale=max(.005,min((self.width()-90)/max(width,1),(self.height()-90)/max(height,1)))
        self.update();self.camera_changed.emit()

    def project(self,point):
        x,y,z=[point[i]-self.center[i] for i in range(3)]
        cy,sy=math.cos(self.yaw),math.sin(self.yaw)
        ce,se=math.cos(self.elevation),math.sin(self.elevation)
        horizontal=x*cy+y*sy;depth=x*sy-y*cy
        return QPointF(self.width()/2+horizontal*self.scale+self.pan[0],self.height()/2+(depth*se-z*ce)*self.scale+self.pan[1])

    def depth(self,p):
        return (p[0]*math.sin(self.yaw)-p[1]*math.cos(self.yaw))*math.cos(self.elevation)+p[2]*math.sin(self.elevation)

    def world_faces(self):
        faces=[]
        if not self.document:return faces
        view=[math.sin(self.yaw)*math.cos(self.elevation),-math.cos(self.yaw)*math.cos(self.elevation),math.sin(self.elevation)]
        for e in self.document.elements:
            if not e.visible or (self.floor is not None and e.floor!=self.floor):continue
            verts=[(x,y,z+e.floor*self.explode) for x,y,z in e.vertices()]
            for indices in e.faces():
                p=[verts[i] for i in indices]
                n=normal(p)
                if sum(a*b for a,b in zip(n,view))<=0 and self.mode!='wire':continue
                if self.section is not None:p=clip_polygon(p,self.section)
                if len(p)<3:continue
                center=tuple(sum(v[i] for v in p)/len(p) for i in range(3))
                faces.append((self.depth(center),e,p,n))
        return sorted(faces,key=lambda item:item[0])

    def paintEvent(self,event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(),QColor('#e4e6e7'))
        if self.grid:
            painter.setPen(QPen(QColor('#cdd1d3'),.7))
            for k in range(-20,21):
                painter.drawLine(self.project((k,-20,-.4)),self.project((k,20,-.4)))
                painter.drawLine(self.project((-20,k,-.4)),self.project((20,k,-.4)))
            for color,a,b in [('#ce7272',(-20,0,-.39),(20,0,-.39)),('#71a574',(0,-20,-.39),(0,20,-.39)),('#668fcb',(0,0,-.4),(0,0,10))]:
                painter.setPen(QPen(QColor(color),1));painter.drawLine(self.project(a),self.project(b))
        self.drawn=[]
        for _,e,points,n in self.world_faces():
            polygon=QPolygonF([self.project(p) for p in points])
            color=QColor(e.color)
            light=.68+.32*max(0,sum(a*b for a,b in zip(n,[.25,-.5,.8])))
            color=QColor.fromRgbF(min(1,color.redF()*light),min(1,color.greenF()*light),min(1,color.blueF()*light))
            chosen=e.id==self.selected_id
            if chosen:color=QColor('#87b5ee')
            painter.setBrush(Qt.NoBrush if self.mode=='wire' else color)
            painter.setPen(QPen(QColor('#347fed') if chosen else QColor('#747d82'),2 if chosen else .7))
            painter.drawPolygon(polygon)
            self.drawn.append((polygon,e,points))
        if self.selected_id and self.document:
            e=next((e for e in self.document.elements if e.id==self.selected_id and e.visible),None)
            if e:
                p=e.position.copy();p[2]+=e.floor*self.explode
                origin=self.project(p)
                for axis,color,label in [(0,'#d45a54','X'),(1,'#58a661','Y'),(2,'#3885ed','Z')]:
                    target=p.copy();target[axis]+=1.6;end=self.project(target)
                    painter.setPen(QPen(QColor(color),2.5));painter.drawLine(origin,end)
                    painter.drawEllipse(end,3,3);painter.drawText(end+QPointF(5,-5),label)
                painter.setPen(QColor('#2d507d'))
                painter.drawText(origin+QPointF(10,22),' × '.join(f'{v:.2f}' for v in e.size)+' m')
        if len(self.measure_points)==2:
            a,b=self.measure_points
            painter.setPen(QPen(QColor('#d69530'),2,Qt.DashLine));painter.drawLine(self.project(a),self.project(b))
            painter.drawText(self.project(a)+QPointF(8,-10),f'{distance(a,b):.3f} m')
        painter.setPen(QColor('#516577'))
        painter.drawText(18,25,'ORTHOGRAPHIC  /  '+self.mode.upper())
        painter.drawText(18,self.height()-18,'Drag: orbit   •   Right drag: pan   •   Wheel: zoom   •   Click: select')
        painter.drawText(self.width()-85,25,'Z ↑')
        painter.end()

    def mousePressEvent(self,event):
        self.last_mouse=event.position();self.dragged=False

    def mouseMoveEvent(self,event):
        if self.last_mouse is None or not event.buttons():return
        delta=event.position()-self.last_mouse
        if abs(delta.x())+abs(delta.y())>1:self.dragged=True
        if event.buttons() & Qt.RightButton:
            self.pan[0]+=delta.x();self.pan[1]+=delta.y()
        else:
            self.yaw+=delta.x()*.008
            self.elevation=min(math.pi/2,max(.05,self.elevation+delta.y()*.006))
        self.last_mouse=event.position();self.update();self.camera_changed.emit()

    def mouseReleaseEvent(self,event):
        if not self.dragged and event.button()==Qt.LeftButton:
            for polygon,e,points in reversed(self.drawn):
                if polygon.containsPoint(event.position(),Qt.OddEvenFill):
                    if self.measure:
                        # Select the nearest projected mesh vertex on the picked face.
                        vertex=min(points,key=lambda p:math.hypot(self.project(p).x()-event.position().x(),self.project(p).y()-event.position().y()))
                        if len(self.measure_points)==2:self.measure_points=[]
                        self.measure_points.append(vertex)
                        if len(self.measure_points)==2:self.measured.emit(distance(*self.measure_points))
                    else:
                        self.selected_id=e.id;self.selected.emit(e.id)
                    self.update();break
        self.last_mouse=None

    def wheelEvent(self,event):
        factor=1.12 if event.angleDelta().y()>0 else 1/1.12
        self.scale=max(.005,min(1000,self.scale*factor));self.update();self.camera_changed.emit()
