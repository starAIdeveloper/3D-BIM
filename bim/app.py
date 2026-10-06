"""Native Qt document editor and undoable modeling operations."""
import argparse
import copy
import math
from pathlib import Path
import sys
import uuid
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QUndoCommand, QUndoStack, QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QToolBar,QTreeWidget,QTreeWidgetItem,
 QDockWidget,QVBoxLayout,QFormLayout,QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox,QPushButton,QLabel,
 QFileDialog,QMessageBox,QColorDialog,QHBoxLayout)
from .model import Document, Element
from .samples import SCENES, sample
from .viewport import Viewport

class SnapshotCommand(QUndoCommand):
    def __init__(self,window,before,after,text):
        super().__init__(text)
        self.window=window;self.before=before;self.after=after
    def undo(self):
        self.window.document=Document.from_dict(copy.deepcopy(self.before));self.window.refresh()
    def redo(self):
        self.window.document=Document.from_dict(copy.deepcopy(self.after));self.window.refresh()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1440,920)
        self.setMinimumSize(1050,650)
        self.document=sample(0);self.path=None;self.selected_id=None;self.updating=False
        self.undo=QUndoStack(self);self.undo.setUndoLimit(100)
        self.viewport=Viewport();self.viewport.document=self.document
        self.setCentralWidget(self.viewport)
        self.viewport.selected.connect(self.select)
        self.viewport.measured.connect(lambda n:self.statusBar().showMessage(f'Vertex-to-vertex distance: {n:.3f} m (current displayed geometry)'))
        self.create_actions();self.create_panels()
        self.undo.cleanChanged.connect(self.update_title)
        self.setStyleSheet('''
         QMainWindow {background:#e4e6e7;} QToolBar {background:#343a40;spacing:5px;border:0;padding:8px;}
         QToolButton {color:#eceff2;padding:8px;border-radius:4px;} QToolButton:hover {background:#4b5662;}
         QToolButton:checked {background:#366caa;} QDockWidget {color:#425366;font-weight:600;}
         QDockWidget::title {background:#dce0e4;padding:9px;} QTreeWidget {background:#f3f5f6;border:0;alternate-background-color:#edf0f2;}
         QTreeWidget::item {padding:5px;} QTreeWidget::item:selected {background:#a8c9ee;color:#253e5a;}
         QLabel {color:#5a6978;} QLineEdit,QDoubleSpinBox,QSpinBox,QComboBox {padding:5px;border:1px solid #ccd3db;border-radius:4px;background:#fff;}
         QPushButton {background:#edf3fb;border:1px solid #bbcbdc;border-radius:4px;padding:8px;color:#31577e;}
         QPushButton:hover {background:#dcecff;} QStatusBar {background:#f1f4f7;color:#5d6c7c;}
        ''')
        self.refresh();QTimer.singleShot(0,self.viewport.fit)
        self.statusBar().showMessage('Ready · metres · local concept model · select geometry to edit')

    def action(self,text,callback,shortcut=None,check=False,toolbar=True):
        a=QAction(text,self);a.setCheckable(check);a.triggered.connect(callback)
        if shortcut:a.setShortcut(shortcut)
        if toolbar:self.tools.addAction(a)
        return a

    def create_actions(self):
        self.tools=QToolBar('Model tools');self.tools.setMovable(False);self.addToolBar(self.tools)
        file=self.menuBar().addMenu('&File')
        for text,slot,key in [('New',self.new_project,'Ctrl+N'),('Open…',self.open_project,'Ctrl+O'),('Save',self.save_project,'Ctrl+S'),('Save as…',self.save_as,'Ctrl+Shift+S'),('Export OBJ…',self.export_obj,None),('Export viewport PNG…',self.export_png,None)]:
            file.addAction(self.action(text,slot,key,toolbar=text in ('New','Open…','Save')))
        edit=self.menuBar().addMenu('&Edit')
        undo=self.undo.createUndoAction(self,'Undo');undo.setShortcut(QKeySequence.Undo)
        redo=self.undo.createRedoAction(self,'Redo');redo.setShortcut(QKeySequence.Redo)
        self.tools.addAction(undo);self.tools.addAction(redo);edit.addAction(undo);edit.addAction(redo)
        self.tools.addSeparator()
        self.action('□ Box',lambda:self.add_element('box'),'B')
        self.action('△ Gable',lambda:self.add_element('gable'),'G')
        self.action('Duplicate',self.duplicate,'Ctrl+D')
        self.action('Delete',self.delete,'Delete')
        self.tools.addSeparator()
        self.action('Fit',self.viewport.fit,'F')
        self.action('Top',lambda:self.camera('top'))
        self.action('Front',lambda:self.camera('front'))
        self.action('Isometric',lambda:self.camera('iso'))
        self.wire_action=self.action('Wireframe',self.toggle_wire,'W',check=True)
        self.section_action=self.action('Section',self.toggle_section,'S',check=True)
        self.explode_action=self.action('Explode',self.toggle_explode,check=True)
        self.measure_action=self.action('Measure',self.toggle_measure,'M',check=True)
        view=self.menuBar().addMenu('&View')
        grid=self.action('Grid',self.toggle_grid,check=True,toolbar=False);grid.setChecked(True);view.addAction(grid)
        self.tools.addSeparator()
        self.scene_picker=QComboBox();self.scene_picker.addItems(SCENES);self.scene_picker.setMinimumWidth(190)
        self.scene_picker.currentIndexChanged.connect(self.change_scene);self.tools.addWidget(self.scene_picker)
        help=self.menuBar().addMenu('&Help')
        help.addAction(self.action('About',lambda:QMessageBox.information(self,'3D-BIM','Original native desktop architectural concept editor.\nBox and gable geometry; not an IFC/B-rep CAD engine.\nCPU-rendered orthographic viewport.\nNo third-party architectural assets.'),toolbar=False))

    def create_panels(self):
        dock=QDockWidget('MODEL EXPLORER',self);dock.setFeatures(QDockWidget.DockWidgetMovable)
        container=QWidget();layout=QVBoxLayout(container)
        self.search=QLineEdit();self.search.setPlaceholderText('Search objects…');self.search.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search)
        self.floor=QComboBox();self.floor.currentIndexChanged.connect(self.floor_changed);layout.addWidget(self.floor)
        self.tree=QTreeWidget();self.tree.setHeaderLabels(['Object','Visible']);self.tree.setColumnWidth(0,210)
        self.tree.setAlternatingRowColors(True);self.tree.itemSelectionChanged.connect(self.tree_selected);self.tree.itemChanged.connect(self.visibility_changed)
        layout.addWidget(self.tree)
        dock.setWidget(container);dock.setMinimumWidth(300);self.addDockWidget(Qt.RightDockWidgetArea,dock)
        props=QDockWidget('ELEMENT PROPERTIES',self);props.setFeatures(QDockWidget.DockWidgetMovable)
        widget=QWidget();form=QFormLayout(widget)
        self.info=QLabel('Select an object');self.info.setWordWrap(True);form.addRow(self.info)
        self.name=QLineEdit();form.addRow('Name',self.name)
        self.category=QLineEdit();form.addRow('Category',self.category)
        self.material=QLineEdit();form.addRow('Material',self.material)
        self.storey=QSpinBox();self.storey.setRange(0,100);form.addRow('Storey',self.storey)
        self.fields={}
        for group,labels in [('size',['Width X','Depth Y','Height Z']),('position',['Position X','Position Y','Position Z'])]:
            for i,label in enumerate(labels):
                spin=QDoubleSpinBox();spin.setDecimals(3);spin.setSingleStep(.1);spin.setSuffix(' m')
                spin.setRange(.001 if group=='size' else -10000,10000);form.addRow(label,spin);self.fields[(group,i)]=spin
        self.rotation=QDoubleSpinBox();self.rotation.setRange(-360,360);self.rotation.setDecimals(1);self.rotation.setSuffix(' °');form.addRow('Rotation Z',self.rotation)
        self.volume=QLabel('');form.addRow('Geometry volume',self.volume)
        self.color_button=QPushButton('Change material color…');self.color_button.clicked.connect(self.change_color);form.addRow(self.color_button)
        self.apply_button=QPushButton('Apply dimensions / transform');self.apply_button.clicked.connect(self.apply_properties);form.addRow(self.apply_button)
        self.section_height=QDoubleSpinBox();self.section_height.setRange(-10000,10000);self.section_height.setDecimals(2);self.section_height.setSuffix(' m');self.section_height.setValue(3.0);self.section_height.valueChanged.connect(self.section_height_changed);form.addRow('Section height Z',self.section_height)
        note=QLabel('Dimensions use XYZ metres with Z up.\nMeasure snaps to face vertices.\nMesh volume is not a material takeoff.');note.setWordWrap(True);form.addRow(note)
        props.setWidget(widget);self.addDockWidget(Qt.RightDockWidgetArea,props)
        self.splitDockWidget(dock,props,Qt.Vertical)

    def update_title(self,*args):
        dirty='' if self.undo.isClean() else ' *'
        self.setWindowTitle(f'{self.document.name}{dirty} | 3D-BIM Desktop')

    def element(self):
        return next((e for e in self.document.elements if e.id==self.selected_id),None)

    def refresh(self):
        self.updating=True
        self.viewport.document=self.document;self.viewport.selected_id=self.selected_id
        self.tree.clear();groups={};self.items={}
        for e in self.document.elements:
            if e.floor not in groups:
                groups[e.floor]=QTreeWidgetItem(self.tree,[f'Level {e.floor}','']);groups[e.floor].setExpanded(True)
            key=(e.floor,e.category)
            if key not in groups:
                groups[key]=QTreeWidgetItem(groups[e.floor],[e.category,'']);groups[key].setExpanded(True)
            item=QTreeWidgetItem(groups[key],[e.name,''])
            item.setData(0,Qt.UserRole,e.id);item.setCheckState(1,Qt.Checked if e.visible else Qt.Unchecked)
            self.items[e.id]=item
        if self.selected_id in self.items:self.tree.setCurrentItem(self.items[self.selected_id])
        elif self.selected_id is not None:self.selected_id=None;self.viewport.selected_id=None
        previous=self.floor.currentData();self.floor.blockSignals(True);self.floor.clear();self.floor.addItem('All storeys',None)
        for f in sorted({e.floor for e in self.document.elements}):self.floor.addItem(f'Level {f}',f)
        index=self.floor.findData(previous);self.floor.setCurrentIndex(max(0,index));self.floor.blockSignals(False)
        self.viewport.floor=self.floor.currentData();self.populate_properties();self.updating=False
        self.filter_tree();self.viewport.update();self.update_title()

    def populate_properties(self):
        e=self.element();enabled=e is not None
        for w in [self.name,self.category,self.material,self.storey,self.rotation,self.color_button,self.apply_button,*self.fields.values()]:w.setEnabled(enabled)
        if not e:self.info.setText('Select an object in the scene or model tree.');self.volume.setText('');return
        self.info.setText(f'{e.id} · {e.kind.upper()}')
        self.name.setText(e.name);self.category.setText(e.category);self.material.setText(e.material);self.storey.setValue(e.floor);self.rotation.setValue(((e.rotation+180)%360)-180)
        for (group,i),widget in self.fields.items():widget.setValue(getattr(e,group)[i])
        self.volume.setText(f'{e.volume():.3f} m³')
        self.color_button.setStyleSheet(f'border-left: 12px solid {e.color};')

    def select(self,id):
        self.selected_id=id;self.viewport.selected_id=id
        self.updating=True
        if id in self.items:self.tree.setCurrentItem(self.items[id]);self.tree.scrollToItem(self.items[id])
        self.populate_properties();self.updating=False;self.viewport.update()

    def tree_selected(self):
        if self.updating:return
        item=self.tree.currentItem()
        if item and item.data(0,Qt.UserRole):self.select(item.data(0,Qt.UserRole))

    def mutate(self,text,operation):
        before=self.document.to_dict();after=copy.deepcopy(self.document)
        operation(after)
        try:Document.from_dict(after.to_dict())
        except ValueError as exc:QMessageBox.warning(self,'Invalid edit',str(exc));return False
        if before==after.to_dict():return True
        self.undo.push(SnapshotCommand(self,before,after.to_dict(),text));return True

    def visibility_changed(self,item,column):
        if self.updating or column!=1:return
        id=item.data(0,Qt.UserRole)
        if not id:return
        visible=item.checkState(1)==Qt.Checked
        # Rebuild only after itemChanged unwinds, so Qt never deletes its active sender.
        def apply_visibility():
            if any(e.id==id for e in self.document.elements):
                self.mutate('Change visibility',lambda d:setattr(next(e for e in d.elements if e.id==id),'visible',visible))
        QTimer.singleShot(0,apply_visibility)

    def filter_tree(self,*args):
        text=self.search.text().casefold()
        def apply(item):
            if item.childCount():
                show=False
                for i in range(item.childCount()):show=apply(item.child(i)) or show
            else:show=text in item.text(0).casefold()
            item.setHidden(not show);return show
        for i in range(self.tree.topLevelItemCount()):apply(self.tree.topLevelItem(i))

    def floor_changed(self,*args):
        if self.updating:return
        self.viewport.floor=self.floor.currentData();self.viewport.update()

    def apply_properties(self):
        if not self.element():return
        def operation(d):
            e=next(e for e in d.elements if e.id==self.selected_id)
            e.name=self.name.text().strip();e.category=self.category.text().strip();e.material=self.material.text().strip();e.floor=self.storey.value();e.rotation=self.rotation.value()
            e.size=[self.fields[('size',i)].value() for i in range(3)];e.position=[self.fields[('position',i)].value() for i in range(3)]
        self.mutate('Edit dimensions and transform',operation)

    def change_color(self):
        e=self.element()
        if not e:return
        c=QColorDialog.getColor(QColor(e.color),self,'Material color')
        if c.isValid():self.mutate('Change material color',lambda d:setattr(next(e for e in d.elements if e.id==self.selected_id),'color',c.name()))

    def add_element(self,kind):
        id=uuid.uuid4().hex;self.selected_id=id
        floor=self.viewport.floor or 0
        self.mutate('Add '+kind,lambda d:d.elements.append(Element(id,'New '+kind,'Custom',floor,[2.,2.,2.],[0.,-7.,1.],kind=kind)))

    def duplicate(self):
        e=self.element()
        if not e:return
        new=e.clone();self.selected_id=new.id;self.mutate('Duplicate element',lambda d:d.elements.append(new))

    def delete(self):
        id=self.selected_id
        if not id:return
        self.mutate('Delete element',lambda d:setattr(d,'elements',[e for e in d.elements if e.id!=id]))

    def camera(self,mode):
        self.viewport.yaw=math.radians(40) if mode=='iso' else 0
        self.viewport.elevation=math.pi/2 if mode=='top' else (.01 if mode=='front' else math.radians(32))
        self.viewport.fit()

    def toggle_wire(self,checked):self.viewport.mode='wire' if checked else 'solid';self.viewport.update()
    def toggle_section(self,checked):self.viewport.section=self.section_height.value() if checked else None;self.viewport.update()
    def section_height_changed(self,value):
        if self.section_action.isChecked():self.viewport.section=value;self.viewport.update()
    def toggle_explode(self,checked):self.viewport.explode=1.5 if checked else 0.;self.viewport.update()
    def toggle_grid(self,checked):self.viewport.grid=checked;self.viewport.update()
    def toggle_measure(self,checked):
        self.viewport.measure=checked;self.viewport.measure_points=[];self.viewport.update()
        self.statusBar().showMessage('Click two visible faces: measurement snaps to nearest face vertices.' if checked else 'Selection mode')

    def confirm_discard(self):
        if self.undo.isClean():return True
        answer=QMessageBox.question(self,'Unsaved changes','Save changes before continuing?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Save)
        return self.save_project() if answer==QMessageBox.Save else answer==QMessageBox.Discard

    def reset_view(self):
        for action in [self.section_action,self.explode_action,self.measure_action,self.wire_action]:action.setChecked(False)
        self.viewport.section=None;self.viewport.explode=0.;self.viewport.measure=False;self.viewport.measure_points=[];self.viewport.mode='solid';self.viewport.floor=None
        self.search.clear();self.selected_id=None;self.floor.blockSignals(True);self.floor.setCurrentIndex(0);self.floor.blockSignals(False)
        self.refresh();self.camera('iso')

    def change_scene(self,index):
        if self.updating:return
        if not self.confirm_discard():
            self.scene_picker.blockSignals(True);self.scene_picker.setCurrentIndex(SCENES.index(self.document.name) if self.document.name in SCENES else 0);self.scene_picker.blockSignals(False);return
        self.document=sample(index);self.path=None;self.undo.clear();self.reset_view()

    def new_project(self):
        if not self.confirm_discard():return
        self.document=Document();self.path=None;self.undo.clear();self.reset_view()

    def open_project(self):
        if not self.confirm_discard():return
        path,_=QFileDialog.getOpenFileName(self,'Open project','','3D-BIM projects (*.bim.json *.json)')
        if path:self.load_path(path)

    def load_path(self,path):
        try:document=Document.load(path)
        except (OSError,ValueError,TypeError) as exc:QMessageBox.warning(self,'Cannot open project',str(exc));return False
        self.document=document;self.path=Path(path);self.undo.clear();self.reset_view();return True

    def save_project(self):
        if self.path is None:return self.save_as()
        try:self.document.save(self.path)
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'Cannot save project',str(exc));return False
        self.undo.setClean();self.statusBar().showMessage(f'Saved {self.path.name}');return True

    def save_as(self):
        path,_=QFileDialog.getSaveFileName(self,'Save project','project.bim.json','3D-BIM projects (*.bim.json)')
        if not path:return False
        old=self.path;self.path=Path(path)
        if self.save_project():return True
        self.path=old;return False

    def export_obj(self):
        path,_=QFileDialog.getSaveFileName(self,'Export mesh','model.obj','Wavefront OBJ (*.obj)')
        if not path:return
        try:self.document.export_obj(path)
        except OSError as exc:QMessageBox.warning(self,'Export failed',str(exc));return
        self.statusBar().showMessage('Exported visible source meshes. View filters and explosion are not baked into OBJ.')

    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,'Export viewport','viewport.png','PNG (*.png)')
        if path and not self.viewport.grab().save(path,'PNG'):QMessageBox.warning(self,'Export failed','Could not write PNG.')

    def closeEvent(self,event):
        event.accept() if self.confirm_discard() else event.ignore()

def main():
    parser=argparse.ArgumentParser(description='Native 3D-BIM architectural concept editor')
    parser.add_argument('project',nargs='?',help='Open a .bim.json project')
    parser.add_argument('--scene',type=int,choices=[0,1,2],default=0,help='Bundled sample scene')
    parser.add_argument('--snapshot',type=Path,help='Capture the desktop window as PNG, then exit')
    options=parser.parse_args()
    app=QApplication([sys.argv[0]]);app.setApplicationName('3D-BIM');app.setOrganizationName('Independent Concept Tools')
    window=MainWindow()
    if options.scene:window.scene_picker.setCurrentIndex(options.scene)
    if options.project and not window.load_path(options.project):return 1
    window.show()
    if options.snapshot:
        def capture():
            success=window.grab().save(str(options.snapshot),'PNG')
            app.exit(0 if success else 1)
        QTimer.singleShot(200,capture)
    return app.exec()
