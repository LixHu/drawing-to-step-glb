# Open CASCADE 工作流

推荐Python 3.12 + `cadquery-ocp==8.0.1.1.0`。工具见 `scripts/cad_export.py`，调用见 `scripts/demo_model.py`。它们处理导出和检查，不会从任意截图自动恢复尺寸；参数仍需要按图提取。

## 建模模式

板状零件画精确封闭轮廓，建立面后沿厚度拉伸，再用圆柱切孔。圆弧用起点、圆弧上的中点、终点创建，不能把弦中点误作圆弧中点。轮廓连接、无自交并保持一致绕序。

```python
from OCP.gp import gp_Pnt, gp_Vec, gp_Ax2, gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut

wire = BRepBuilderAPI_MakeWire()
for edge in edges:  # 精确直线及圆弧
    wire.Add(edge)
assert wire.IsDone()
face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
solid = BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, thickness_mm)).Shape()
cutter = BRepPrimAPI_MakeCylinder(
    gp_Ax2(gp_Pnt(hole_x, hole_y, -1), gp_Dir(0, 0, 1)),
    hole_diameter_mm / 2, thickness_mm + 2,
).Shape()
operation = BRepAlgoAPI_Cut(solid, cutter)
operation.Build()
assert operation.IsDone()
solid = operation.Shape()
```

圆管用同轴圆柱相减，内孔刀具两端各伸出一点。独立验证：`π × (OD² - ID²) / 4 × length`。管长与总高分别命名。

螺栓可用公称直径圆柱加六角柱，螺母用六角柱切孔。记录螺纹、倒角等简化，未建螺旋牙型不能称完整制造模型。

## 已验证的绑定差异

- OCP 8.0用 `TopoDS.Face(shape)`，不要照搬旧版 `TopoDS.Face_s`。
- 此绑定的 `Bnd_Box.Get()`可能抛出未注册 `Bnd_Box::Limits` 的TypeError，改用 `CornerMin()`、`CornerMax()`读XYZ。
- `BRepBndLib.AddOptimal_s(shape, box, False, False)`关闭三角化和形状公差扩展，使STEP重读对比基于解析几何。默认调用可能混入网格近似误差。
- 通过 `BRep_Tool.Triangulation_s(face, location)`取得各Face网格，应用 `location.Transformation()`；`TopAbs_REVERSED`面交换三角形两顶点保证绕序。
- `trimesh.graph.smooth_shade`需图计算后端；包含`networkx`避免 `no graph engines available`。
- 离散精度用mm，角度用弧度。GLB顶点最后乘0.001，不再添加1000倍节点变换。

## 精度与恢复

实体无效先修正闭合、布尔、相切和面方向。布尔失败检查尺寸链和工具轴向，不随意改变图纸尺寸。不要删有效性断言以获得文件，也不要悄悄用网格STEP替代精确实体。

STEP重读成功还需比对实体数、尺寸和体积。装配中共面接触正常，不为了整套成为一个实体而把螺栓与板材融合。

GLB是离散表示，记录网格相对BRep的体积和包围盒误差。默认允许体积相对误差0.1%、包围盒约2倍线性离散公差；精细小孔/薄壁需按需要收紧。

## 渲染和脚本

工具带无需桌面CAD窗口的软件深度缓冲渲染，显示正视、斜视；不是正式二维工程图。用户需要局部细节时另加视角。

不要导入旧案例的顶层生成脚本，那会执行旧写文件操作。复用无顶层写操作的导出模块，把新任务建模放在独立主函数。
