"""Three original architectural concept scenes; no third-party assets."""
from .model import Document, Element

SCENES = ['Gabled residence', 'Ground-floor layout', 'Modern courtyard villa']

def sample(index=0):
    elements=[]
    def add(name,category,size,pos,color='#d4d5d1',floor=0,material='Concrete',kind='box',rotation=0):
        elements.append(Element(f'E-{len(elements)+1:04d}',name,category,floor,list(size),list(pos),color,material,kind,True,rotation))
    add('Site plinth','Site',[20,18,.18],[0,0,-.25],'#c6c8bf',material='Paving')
    modern=index==2
    stories=1 if index==1 else 2
    for f in range(stories):
        z=f*3.1
        add(f'Level {f} slab','Slabs',[12,10,.22],[0,0,z],floor=f)
        # Segmented elevations leave physical openings rather than covering them with opaque walls.
        for side in [-1,1]:
            y=side*5
            add(f'L{f} south/north sill {side}','Walls',[12,.22,.65],[0,y,z+.42],floor=f)
            add(f'L{f} south/north lintel {side}','Walls',[12,.22,.4],[0,y,z+2.85],floor=f)
            for x in [-5.9,-2.0,2.0,5.9]:
                add(f'L{f} facade pier {x}/{side}','Walls',[.26,.22,2.3],[x,y,z+1.7],floor=f)
            for x in [-3.9,0,3.9]:
                add(f'L{f} glazing {x}/{side}','Windows',[3.45,.07,1.9],[x,y,z+1.65],'#89a5af',f,'Glazing')
                for dx in [-1.7,0,1.7]:
                    add(f'L{f} window frame {x+dx}/{side}','Frames',[.06,.16,1.95],[x+dx,y-side*.08,z+1.65],'#343d45',f,'Aluminium')
        for x in [-6,6]:
            add(f'L{f} end wall {x}','Walls',[.22,10,2.85],[x,0,z+1.55],floor=f)
        add(f'L{f} dividing wall','Walls',[.17,7,2.6],[0,1.4,z+1.4],floor=f)
        add(f'L{f} room partition','Walls',[5.7,.17,2.6],[-3,1.1,z+1.4],floor=f)
        add(f'L{f} doorway header','Walls',[1.5,.18,.35],[1.8,0,z+2.7],floor=f)
        add(f'L{f} partition wing','Walls',[2.6,.18,2.6],[4.5,0,z+1.4],floor=f)
        for x in [-3,3]:
            add(f'L{f} sofa base {x}','Furniture',[2.4,.95,.42],[x,2.8,z+.38],'#a9a69b',f,'Fabric')
            add(f'L{f} sofa back {x}','Furniture',[2.4,.2,.8],[x,3.2,z+.65],'#b9b6ab',f,'Fabric')
            add(f'L{f} table {x}','Furniture',[1.4,.8,.13],[x,.5,z+.72],'#957a5b',f,'Timber')
    if index==0:
        add('Main pitched roof','Roofs',[12.8,10.8,2.3],[0,0,7.25],'#424d59',1,'Slate','gable')
        add('Entry annex slab','Slabs',[4,3,.2],[-4,-6.6,.05])
        for x in [-6,-2]:add('Entry annex side','Walls',[.2,3,2.9],[x,-6.5,1.55])
        add('Entry roof','Roofs',[4.4,3.4,.23],[-4,-6.5,3.1],'#56616b',material='Slate')
        add('Entry door','Doors',[1.3,.15,2.3],[-3.6,-8,1.25],'#414648',material='Timber')
    if modern:
        add('Flat roof','Roofs',[12.8,10.8,.35],[0,0,6.25],'#535e63',1)
        for x in [-6.35,6.35]:add('Roof parapet','Roofs',[.15,10.7,.45],[x,0,6.6],'#434c55',1)
        for y in [-5.3,5.3]:add('Roof fascia','Roofs',[12.8,.16,.45],[0,y,6.5],'#434c55',1)
        add('Upper terrace','Slabs',[12,2.2,.2],[0,-6,3.1],'#b6bbb8',1)
        for x in range(-11,12):
            add('Timber facade fin','Cladding',[.085,.3,2.8],[x*.51,5.18,4.65],'#a87c48',1,'Timber')
        for x in [-5.8,5.8]:add('Balcony upright','Railings',[.06,2,1],[x,-6,3.7],'#3a464c',1,'Metal')
        add('Balcony rail','Railings',[11.7,.06,.06],[0,-7,4.2],'#3a464c',1,'Metal')
        add('Terrace decking','Site',[12,3,.16],[0,-6.9,.0],'#b29a75',material='Timber')
        add('Lawn','Site',[5,13,.12],[8,0,-.08],'#8c9d77',material='Grass')
    for k in range(4):add(f'Entry step {k+1}','Site',[5,1.2,.16],[0,-6.5-k*.7,-.05-k*.14],'#bcbfbb',material='Stone')
    if index!=1:
        for x,y in [(-8,4),(8,4),(8,-4),(-8,-3)]:
            add('Tree trunk','Landscape',[.2,.2,2.1],[x,y,.9],'#887254',material='Timber')
            for dz,s in [(1.7,1.4),(2.5,1.8),(3.3,1.1)]:add('Tree canopy','Landscape',[s,s,.9],[x,y,dz],'#78936a',material='Foliage')
    return Document(SCENES[index],elements)
