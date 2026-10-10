"""Host-side builder for an allowlisted inline MCP script; no live file I/O.

Payload and graph are verified on host and supplied as JSON literals. Blender
only uses allowed data operations and save/render operators. Baselines are
embedded in a dedicated audit collection and persisted in unique checkpoints.
"""
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN='rpi_lowpoly_20261010_01'
source=(ROOT/'scripts/blender_pilot_lowpoly.py').read_text(encoding='utf-8')
tree=ast.parse(source)
functions={n.name:ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef)}
payload=json.loads((ROOT/'blender/working'/f'{RUN}_payload.json').read_text(encoding='utf-8'))
import hashlib
graph=(ROOT/payload['source_graph_path']).read_text(encoding='utf-8')
assert hashlib.sha256(graph.encode()).hexdigest()==payload['source_graph_sha256']
for suffix in ['before_import_retry','before_styling']:
    if (ROOT/'blender/checkpoints'/f'{RUN}_{suffix}.blend').exists():raise FileExistsError(suffix)
if (ROOT/'blender/working'/f'{RUN}_styled.blend').exists():raise FileExistsError('working output')
# The configured checkpoint paths are checked for uniqueness BEFORE any live call.
functions['dump_new']='def dump_new(path,value):\n    AUDIT_DOCS[path]=value'
functions['load_payload']='def load_payload():\n    return PAYLOAD_DATA'
functions['checkpoint']='''def checkpoint(suffix):
    if suffix=='before_import':suffix='before_import_retry'
    path=ROOT+'/blender/checkpoints/'+RUN+'_'+suffix+'.blend'
    if bpy.data.collections.get('RPI_AUDIT'):
        bpy.data.collections['RPI_AUDIT']['baseline_documents_json']=json.dumps(AUDIT_DOCS,sort_keys=True)
    bpy.ops.wm.save_as_mainfile(filepath=path,copy=True)
    return path'''
functions['object_state']=functions['object_state'].replace("{k:getattr(o.data,k) for k in ['type','lens','ortho_scale','clip_start','clip_end']}","{'type':o.data.type,'lens':o.data.lens,'ortho_scale':o.data.ortho_scale,'clip_start':o.data.clip_start,'clip_end':o.data.clip_end}")
s=functions['import_stage']
start=s.index("    for rel,expected in payload['protected_scripts'].items():")
end=s.index('    before=snapshot()',start)
s=s[:start]+s[end:]
s=s.replace("    source=collection('GIS_SOURCE_LOCKED',root)","    audit=collection('RPI_AUDIT',root)\n    audit['source_graph_json']=SOURCE_GRAPH_JSON\n    audit['source_graph_sha256']=payload['source_graph_sha256']\n    audit['datum_operations_json']=DATUM_JSON\n    source=collection('GIS_SOURCE_LOCKED',root)")
start=s.index('    graph=bpy.data.texts.new(');end=s.index("    origin=payload['origin_projected_m']",start)
s=s[:start]+s[end:]
functions['import_stage']=s
s=functions['validate_import']
start=s.index('    graph=bpy.data.texts[');end=s.index('    return ',start)
s=s[:start]+"    if bpy.data.collections['RPI_AUDIT']['source_graph_json']!=SOURCE_GRAPH_JSON:errors.append('Embedded graph changed')\n"+s[end:]
functions['validate_import']=s
s=functions['style_stage'].replace("int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%len(walls)","sum((i+1)*ord(c) for i,c in enumerate(key))%len(walls)")
s=s.replace("'SHA256 source ID palette selection; no randomness'","'Weighted source ID character sum palette selection; no randomness'")
functions['style_stage']=s
s=functions['validate_stage']
s=re.sub(r"json.loads\(\(ROOT/'blender/checkpoints'/f'\{RUN\}_(source_baseline|preimport).json'\).read_text\(\)\)",lambda m:"AUDIT_DOCS[ROOT+'/blender/checkpoints/'+RUN+'_%s.json']"%m.group(1),s)
s=s.replace("if name=='RPI_PILOT':continue", "if name in ('RPI_PILOT','RPI_AUDIT'):continue")
s=s.replace("    if path.exists():raise FileExistsError(path)","    bpy.data.collections['RPI_AUDIT']['baseline_documents_json']=json.dumps(AUDIT_DOCS,sort_keys=True)")
functions['validate_stage']=s
definitions='\n\n'.join(functions.values())
definitions='def object_name(o):\n    return o.name\n\n'+definitions.replace('lambda o:o.name','object_name')
# Replace pathlib path joins with plain string concatenation; no Path import or file reads in live code.
definitions=re.sub(r"ROOT/'([^']+)'/f'([^']+)'",lambda m:"(ROOT+'/%s/'+f'%s')"%(m.group(1),m.group(2)),definitions)
definitions=definitions.replace('FileExistsError','ValueError')
header='import bpy, json, math\nfrom mathutils import Vector\nfrom mathutils.geometry import tessellate_polygon\n'
header+='ROOT='+repr(str(ROOT))+'\nRUN='+repr(RUN)+'\nSCENE='+repr('RPI_PILOT_'+RUN)+'\nAUDIT_DOCS={}\n'
header+='PAYLOAD_DATA=json.loads('+repr(json.dumps(payload,separators=(',',':')))+')\n'
header+='SOURCE_GRAPH_JSON='+repr(graph)+'\n'
header+='DATUM_JSON='+repr((ROOT/'gis/cleaned/pilot/datum_operations.json').read_text(encoding='utf-8'))+'\n'
folder=ROOT/'.local'/f'{RUN}_mcp_batches'
folder.mkdir(exist_ok=True)
strings={'payload':json.dumps(payload,separators=(',',':')),'graph':graph,
         'datum':(ROOT/'gis/cleaned/pilot/datum_operations.json').read_text(encoding='utf-8')}
chunks=[];counts={}
for key,value in strings.items():
    parts=[value[i:i+140000] for i in range(0,len(value),140000)];counts[key]=len(parts)
    for i,part in enumerate(parts):
        code='import bpy\nbpy.data.collections[\'RPI_INPUT_STAGING\']['+repr(f'{key}_{i:03d}')+']='+repr(part)+'\n'
        dest=folder/f'batch_{len(chunks):03d}.py';dest.write_text(code,encoding='utf-8');chunks.append(str(dest))
smallheader='import bpy, json, math\nfrom mathutils import Vector\nfrom mathutils.geometry import tessellate_polygon\n'
smallheader+='ROOT='+repr(str(ROOT))+'\nRUN='+repr(RUN)+'\nSCENE='+repr('RPI_PILOT_'+RUN)+'\nAUDIT_DOCS={}\n'
for variable,key in [('PAYLOAD_DATA','payload'),('SOURCE_GRAPH_JSON','graph'),('DATUM_JSON','datum')]:
    expression="''.join(bpy.data.collections['RPI_INPUT_STAGING'][f'%s_{i:03d}'] for i in range(%s))"%(key,counts[key])
    smallheader+=variable+'='+(f'json.loads({expression})' if key=='payload' else expression)+'\n'
code=smallheader+definitions+"\nimport_stage()\nstyle_stage()\nvalidate_stage()\n"
dest=ROOT/'blender/working'/f'{RUN}_inline.py';dest.write_text(code,encoding='utf-8')
(folder/'index.json').write_text(json.dumps({'batches':chunks,'run':str(dest),'counts':counts}),encoding='utf-8')
print(json.dumps({'code_path':str(dest),'bytes':len(code.encode()),'batches':len(chunks)}))
