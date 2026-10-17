"""Exact OCP solids -> named STEP AP214 + metre/Y-up GLB + validation + preview.

No modelling or filesystem writes occur on import. All input geometry is in mm.
Set CODEX_CAD_PACKAGES only when reusing a separate dependency installation.
"""
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if os.environ.get('CODEX_CAD_PACKAGES'):
    sys.path.insert(0, os.environ['CODEX_CAD_PACKAGES'])

import numpy as np
import trimesh
from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_DocumentTool


@dataclass
class Part:
    name: str
    shape: object
    color: tuple = (140, 158, 178, 255)


def solids(shape):
    result = []
    it = TopExp_Explorer(shape, TopAbs_SOLID)
    while it.More():
        result.append(it.Current())
        it.Next()
    return result


def properties(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    lo, hi = box.CornerMin(), box.CornerMax()
    prop = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, prop)
    return dict(valid=bool(BRepCheck_Analyzer(shape).IsValid()),
                solids=len(solids(shape)), volume_mm3=prop.Mass(),
                bounds_mm=[lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z()])


def compound(parts):
    shape, builder = TopoDS_Compound(), BRep_Builder()
    builder.MakeCompound(shape)
    for part in parts:
        builder.Add(shape, part.shape)
    return shape


def tessellate(shape, linear_mm=0.015, angular_rad=0.06):
    BRepMesh_IncrementalMesh(shape, linear_mm, False, angular_rad, True).Perform()
    vertices, faces = [], []
    it = TopExp_Explorer(shape, TopAbs_FACE)
    while it.More():
        face = TopoDS.Face(it.Current())
        location = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, location)
        if tri is None:
            raise ValueError('A face has no triangulation')
        offset = len(vertices)
        for i in range(1, tri.NbNodes() + 1):
            p = tri.Node(i).Transformed(location.Transformation())
            vertices.append((p.X(), p.Y(), p.Z()))
        for i in range(1, tri.NbTriangles() + 1):
            a, b, c = tri.Triangle(i).Get()
            if face.Orientation() == TopAbs_REVERSED:
                b, c = c, b
            faces.append((offset + a - 1, offset + b - 1, offset + c - 1))
        it.Next()
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    if not (mesh.is_watertight and mesh.is_winding_consistent and mesh.volume > 0):
        raise ValueError('Tessellation is not a closed, consistently oriented solid')
    return mesh


def write_step(parts, path, title):
    doc = TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root = st.NewShape()
    st.SetShape(root, compound([]))
    TDataStd_Name.Set_s(root, TCollection_ExtendedString(title))
    for part in parts:
        label = st.AddShape(part.shape, False)
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(part.name))
        rgb = part.color
        ct.SetColor(label, Quantity_Color(*(v / 255 for v in rgb[:3]), Quantity_TOC_RGB), XCAFDoc_ColorGen)
        instance = st.AddComponent(root, label, TopLoc_Location())
        TDataStd_Name.Set_s(instance, TCollection_ExtendedString(part.name))
    st.UpdateAssemblies()
    Interface_Static.SetCVal_s('write.step.schema', 'AP214IS')
    Interface_Static.SetCVal_s('write.step.unit', 'MM')
    writer = STEPCAFControl_Writer()
    writer.SetNameMode(True)
    writer.SetColorMode(True)
    if not writer.Transfer(doc) or writer.Write(str(path)) != IFSelect_RetDone:
        raise RuntimeError('STEP export failed')


def _same_properties(a, b):
    return (a['solids'] == b['solids'] and b['valid'] and
            np.allclose(a['bounds_mm'], b['bounds_mm'], rtol=0, atol=1e-5) and
            math.isclose(a['volume_mm3'], b['volume_mm3'], rel_tol=1e-9, abs_tol=1e-5))


def export_model(parts, output_dir, stem, *, dimensions_mm=None, assumptions=None,
                 expected_bounds_mm=None, linear_mm=0.015, angular_rad=0.06,
                 max_volume_relative_error=0.001, preview=True):
    """Export and validate; refuses existing output names rather than overwriting.

    Each Part contains one solid in global coordinates. Explicitly set names,
    geometry, and units before calling. Returns the validation report.
    """
    parts = list(parts)
    if not parts or len({p.name for p in parts}) != len(parts):
        raise ValueError('Provide nonempty parts with unique names')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', stem):
        raise ValueError('Use a simple ASCII filename stem without directory components')
    if linear_mm <= 0 or not 0 < angular_rad < math.pi or max_volume_relative_error <= 0:
        raise ValueError('Use positive tessellation and error tolerances')
    folder = Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    paths = dict(step=folder / f'{stem}.step', glb=folder / f'{stem}.glb',
                 validation=folder / f'{stem}_validation.json', preview=folder / f'{stem}_preview.png')
    for path in paths.values():
        if path.exists():
            raise FileExistsError(f'Preserve existing output; use a new stem or directory: {path}')
    reports, meshes = [], []
    for part in parts:
        if not part.name or len(part.color) != 4 or any(not 0 <= v <= 255 for v in part.color):
            raise ValueError('Use nonempty part names and RGBA values from 0 to 255')
        prop = properties(part.shape)
        if not (prop['valid'] and prop['solids'] == 1 and prop['volume_mm3'] > 0):
            raise ValueError(f'{part.name}: expected one valid solid with positive volume')
        mesh = tessellate(part.shape, linear_mm, angular_rad)
        volume_error = abs(mesh.volume - prop['volume_mm3']) / prop['volume_mm3']
        bbox_error = float(np.max(np.abs(mesh.bounds.reshape(-1) - prop['bounds_mm'])))
        if volume_error > max_volume_relative_error or bbox_error > linear_mm * 2 + 1e-5:
            raise ValueError(f'{part.name}: refine tessellation; volume error={volume_error}, bounds error mm={bbox_error}')
        reports.append(dict(name=part.name, cad=prop, triangles=len(mesh.faces),
                            mesh_volume_relative_error=float(volume_error), mesh_bounds_error_mm=bbox_error))
        meshes.append(mesh)
    original = properties(compound(parts))
    if expected_bounds_mm is not None and not np.allclose(original['bounds_mm'], expected_bounds_mm, rtol=0, atol=1e-5):
        raise ValueError(f'Design dimensions differ from expected bounds: {original["bounds_mm"]}')
    write_step(parts, paths['step'], stem)
    reader = STEPControl_Reader()
    if reader.ReadFile(str(paths['step'])) != IFSelect_RetDone or reader.TransferRoots() != 1:
        raise RuntimeError('STEP re-import failed')
    loaded = reader.OneShape()
    roundtrip = properties(loaded)
    if not _same_properties(original, roundtrip):
        raise ValueError('STEP assembly count, dimensions or volume changed on re-import')
    unmatched = [properties(s) for s in solids(loaded)]
    for report in reports:
        for i, prop in enumerate(unmatched):
            if _same_properties(report['cad'], prop):
                report['step_roundtrip'] = unmatched.pop(i)
                break
        else:
            raise ValueError(f'No matching re-imported solid for {report["name"]}')
    scene = trimesh.Scene()
    for part, mesh in zip(parts, meshes):
        display = trimesh.graph.smooth_shade(mesh.copy(), angle=np.radians(35))
        display.apply_scale(0.001)
        display.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
            name=part.name, baseColorFactor=part.color, metallicFactor=0.6, roughnessFactor=0.4))
        display.metadata['inferred_detail'] = part.name.startswith('INFERRED_')
        scene.add_geometry(display, geom_name=part.name, node_name=part.name)
    scene.metadata.update(dict(units='meters', source_units='mm', dimensions_mm=dimensions_mm or {}, assumptions=assumptions or []))
    scene.export(str(paths['glb']))
    imported = trimesh.load(paths['glb'], force='scene')
    if set(imported.geometry) != {p.name for p in parts}:
        raise ValueError('GLB component names/count changed')
    if not np.allclose(imported.bounds, scene.bounds, rtol=0, atol=1e-6):
        raise ValueError('GLB assembly bounds/placement changed')
    for part, mesh, report in zip(parts, meshes, reports):
        geometry = imported.geometry[part.name]
        geometry.merge_vertices()
        if not (geometry.is_watertight and geometry.is_winding_consistent and geometry.volume > 0):
            raise ValueError(f'{part.name}: re-imported GLB is not closed and oriented')
        if not np.allclose(geometry.bounds, mesh.bounds * .001, rtol=0, atol=1e-6):
            raise ValueError(f'{part.name}: GLB bounds changed')
        if not math.isclose(geometry.volume, mesh.volume * 1e-9, rel_tol=1e-4, abs_tol=1e-15):
            raise ValueError(f'{part.name}: GLB volume changed')
        report['glb_watertight_after_merge'] = True
    report = dict(status='passed', step_schema='AP214', step_units='mm', glb_units='m', up_axis='Y',
                  dimensions_mm=dimensions_mm or {}, assumptions=assumptions or [],
                  linear_deflection_mm=linear_mm, angular_deflection_rad=angular_rad,
                  assembly=original, step_roundtrip=roundtrip, parts=reports,
                  glb_bounds_m=imported.bounds.tolist(), solidworks_open_tested=False,
                  files={k: str(v) for k, v in paths.items() if k != 'preview' or preview})
    if preview:
        render_preview(parts, meshes, paths['preview'], stem)
    paths['validation'].write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return report


def render_preview(parts, meshes, path, title):
    """Front and oblique views of actual exported tessellation; no external GUI."""
    from PIL import Image, ImageDraw, ImageFont
    width, height = 1400, 1000
    pixels = np.full((height, width, 3), [244, 246, 249], dtype=np.uint8)
    bounds = np.array([m.bounds for m in meshes])
    centre = (bounds[:, 0].min(axis=0) + bounds[:, 1].max(axis=0)) / 2
    ay, ax = math.radians(-28), math.radians(12)
    ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    light = np.array([-.35, .45, 1.]); light /= np.linalg.norm(light)
    for panel, rotation in enumerate([np.eye(3), rx @ ry]):
        all_points = [(m.vertices - centre) @ rotation.T for m in meshes]
        lo = np.concatenate(all_points).min(axis=0); hi = np.concatenate(all_points).max(axis=0)
        scale = min(600 / max(hi[0] - lo[0], 1e-9), 750 / max(hi[1] - lo[1], 1e-9))
        zbuffer = np.full((height, width), -np.inf)
        for part, mesh, points in zip(parts, meshes, all_points):
            points = points.copy()
            points[:, 0] = (points[:, 0] - (lo[0] + hi[0]) / 2) * scale + 350 + panel * 700
            points[:, 1] = 550 - (points[:, 1] - (lo[1] + hi[1]) / 2) * scale
            for indices, normal in zip(mesh.faces, mesh.face_normals @ rotation.T):
                if normal[2] <= 1e-8:
                    continue
                tri = points[indices]; x, y, z = tri.T
                x0 = max(panel * 700, int(math.floor(x.min()))); x1 = min((panel + 1) * 700 - 1, int(math.ceil(x.max())))
                y0 = max(145, int(math.floor(y.min()))); y1 = min(945, int(math.ceil(y.max())))
                if x0 > x1 or y0 > y1:
                    continue
                den = (y[1]-y[2])*(x[0]-x[2]) + (x[2]-x[1])*(y[0]-y[2])
                if abs(den) < 1e-10:
                    continue
                yy, xx = np.mgrid[y0:y1+1, x0:x1+1]; xx = xx+.5; yy = yy+.5
                a = ((y[1]-y[2])*(xx-x[2]) + (x[2]-x[1])*(yy-y[2])) / den
                b = ((y[2]-y[0])*(xx-x[2]) + (x[0]-x[2])*(yy-y[2])) / den
                c = 1-a-b; depth = a*z[0]+b*z[1]+c*z[2]
                region = zbuffer[y0:y1+1, x0:x1+1]
                visible = (a >= -1e-8) & (b >= -1e-8) & (c >= -1e-8) & (depth > region)
                region[visible] = depth[visible]
                color = np.array(part.color[:3]) * (.42 + .55 * max(0., float(normal @ light)))
                pixels[y0:y1+1, x0:x1+1][visible] = color
    image = Image.fromarray(pixels); draw = ImageDraw.Draw(image)
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    def font(size):
        return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default()
    draw.text((35, 25), title, font=font(28), fill='#172334')
    draw.text((295, 100), 'Front', font=font(22), fill='#526174')
    draw.text((1000, 100), 'Oblique', font=font(22), fill='#526174')
    draw.text((35, 960), 'Actual exported geometry | STEP: mm | GLB: m | Y up', font=font(18), fill='#526174')
    image.save(path)
