"""Run a small reproducible export example, not an automatic image converter.

python demo_model.py --out <new-directory> [--assembly]
Requires dependencies from requirements.txt or CODEX_CAD_PACKAGES.
"""
import argparse
import math
from cad_export import Part, export_model, properties
from OCP.gp import gp_Pnt, gp_Ax2, gp_Dir
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut


def cut(a, b):
    operation = BRepAlgoAPI_Cut(a, b)
    operation.Build()
    if not operation.IsDone():
        raise RuntimeError('Cut failed')
    return operation.Shape()


def cylinder(at, direction, radius, length):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*at), gp_Dir(*direction)), radius, length).Shape()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--assembly', action='store_true')
    args = parser.parse_args()
    plate = BRepPrimAPI_MakeBox(100, 60, 12).Shape()
    for x in [20, 80]:
        plate = cut(plate, cylinder((x, 30, -1), (0, 0, 1), 6, 14))
    expected_volume = (100*60 - 2*math.pi*6**2)*12
    assert math.isclose(properties(plate)['volume_mm3'], expected_volume, abs_tol=1e-6)
    parts = [Part('Plate_t12_two_D12_holes', plate)]
    dimensions = dict(plate_mm=[100, 60, 12], hole_diameter=12, hole_centres=[[20, 30], [80, 30]])
    expected_bounds = [0, 0, 0, 100, 60, 12]
    if args.assembly:
        tube = cut(cylinder((50, 60, 6), (0, 1, 0), 15, 100),
                   cylinder((50, 59, 6), (0, 1, 0), 12, 102))
        assert math.isclose(properties(tube)['volume_mm3'], math.pi*(15**2-12**2)*100, abs_tol=1e-6)
        parts.append(Part('Tube_OD30_wall3_length100', tube, (192, 199, 208, 255)))
        dimensions['tube_mm'] = dict(outer_diameter=30, wall=3, length=100)
        expected_bounds = [0, 0, -9, 100, 160, 21]
    report = export_model(parts, args.out, 'demo_assembly' if args.assembly else 'demo_plate',
                          dimensions_mm=dimensions, assumptions=[], expected_bounds_mm=expected_bounds)
    print(f"Passed: {len(report['parts'])} part(s); outputs: {args.out}")


if __name__ == '__main__':
    main()
