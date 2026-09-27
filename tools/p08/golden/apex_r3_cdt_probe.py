from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
import json
vertices=[Vector((0,0)),Vector((1,0)),Vector((1,1)),Vector((0,1)),Vector((.3,.3)),Vector((.7,.3)),Vector((.7,.7)),Vector((.3,.7))]
result=delaunay_2d_cdt(vertices,[(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4)],[],0,.000001)
print('CDT_API_PROBE '+json.dumps({'outputParts':len(result),'vertices':len(result[0]),'faces':[list(f) for f in result[2]]}))
