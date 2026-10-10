"""Prepare inline code for Blender MCP safe mode, without disabling its protections.

Usage: python scripts/build_pass02_run.py --mode apply|validate
Send the resulting UTF-8 script as execute_blender_code.code. This host program
does not connect to Blender or modify the live scene. Existing run outputs block
reapplication; use a new run ID and distinct artifact names for another pass.
"""
import argparse
import ast
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN='rpi_lowpoly_20261010_pass02'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['apply','validate'],required=True)
    args=parser.parse_args()
    if args.mode=='apply':
        for path in [ROOT/'blender/checkpoints'/f'{RUN}_before_changes.blend',
                     ROOT/'blender/working'/f'{RUN}_v01.blend']:
            if path.exists():raise FileExistsError(f'Refusing to repeat a saved run: {path}')
    source=(ROOT/'blender/working/rpi_lowpoly_20261010_01_validate.py').read_text()
    names={'object_name','plain','props','object_state'}
    helpers='\n\n'.join(ast.get_source_segment(source,node) for node in ast.parse(source).body
                       if isinstance(node,ast.FunctionDef) and node.name in names)
    landmarks=(ROOT/'blender/working'/f'{RUN}_landmarks.json').read_text()
    json.loads(landmarks)
    code='import bpy, json, math\nfrom mathutils import Vector\n'+helpers
    code+='\nLANDMARKS=json.loads('+repr(landmarks)+')\n'
    code+=(ROOT/'scripts/blender_pass02.py').read_text()
    if args.mode=='apply':code+='\nbegin_pass02()\n'
    code+='\nvalidate_pass02()\n'
    ast.parse(code)
    out=ROOT/'.local'/f'{RUN}_{args.mode}.py'
    out.parent.mkdir(exist_ok=True)
    out.write_text(code,encoding='utf-8')
    print(out)

if __name__=='__main__':main()
