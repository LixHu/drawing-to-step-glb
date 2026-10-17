# 图纸转 STEP 和 GLB

`drawing-to-step-glb` 是一个 Codex 技能：根据机械工程图、尺寸截图或草图建立参数化 CAD 实体，导出 SolidWorks 可导入的 STEP，以及从同一实体生成的 GLB。

识图和建模由使用技能的智能体完成，附带的 Python 工具负责实体导出、重新读取校验和几何预览。它不是无需核对尺寸的一键图片转换器。

## 能做什么

- 核对尺寸链、孔径、板厚、圆角和装配净空，区分图纸尺寸、用户补充尺寸与补足项。
- 生成精确 BRep 实体，输出 AP214 STEP，支持命名装配组件和颜色。
- 从同一实体离散生成 GLB，统一从毫米转换为米，保留独立零件节点。
- 检查实体有效性、STEP 重新读取后的尺寸及体积、GLB 网格闭合和单位。
- 生成真实几何的正视、斜视预览，以及 JSON 校验报告。
- 保留参数化建模脚本，便于调整尺寸后重新导出。

## 安装与使用

### 在线安装

支持直接从 GitHub 在线安装，安装器会下载技能说明、脚本和参考资料并放到对应技能目录。当前仓库根目录已经包含 `SKILL.md`，可以直接被安装器发现。

以下按 GitHub 仓库 `LixHu/drawing-to-step-glb` 编写；需要先将本目录推送到该仓库。若使用其他账号或仓库名，将命令中的地址替换成实际地址。

使用 [Skills CLI](https://github.com/vercel-labs/skills)，在已安装 Node.js / npm 的电脑上执行：

```bash
npx skills add LixHu/drawing-to-step-glb --skill drawing-to-step-glb -g -a codex
```

`-g` 表示安装到用户范围，`-a codex` 表示安装给 Codex。也可以直接把下列内容发给 Codex，让内置安装器完成：

```text
使用 $skill-installer，从 https://github.com/LixHu/drawing-to-step-glb 安装技能。
技能在仓库根目录，路径为 .，安装名称为 drawing-to-step-glb。
```

Codex 的内置安装器支持从其他 GitHub 仓库安装技能，见 [官方说明](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use)。安装器若提示已存在同名技能，应按实际需要保留或更新原版本。

在线安装负责安装技能文件；首次建模时，智能体会按技能要求检测 CAD 环境并按需准备独立 Python 依赖。

### 调用技能

安装完成后，在 Codex 会话中附上图纸，然后输入：

```text
使用 $drawing-to-step-glb，根据这张图生成 STEP 和 GLB。
保留原有模型；尺寸冲突先说明，缺失尺寸列为补足项。
```

圆管建议同时提供外径、壁厚和管长，并注明长度指管长还是装配总高。总装图和零件详图一起提供时，可以更准确地确定连接结构。

### 本地开发安装

开发或离线调试时，也可以将本仓库目录放到个人技能目录，目录名保持为 `drawing-to-step-glb`：

```text
~/.codex/skills/drawing-to-step-glb/
├── SKILL.md
├── agents/openai.yaml
├── references/
└── scripts/
```

Windows 对应目录为 `%USERPROFILE%\.codex\skills\drawing-to-step-glb`。已有同名技能时先保留需要的版本。

## 开发者：单独运行 Python 导出工具

建议使用 Python 3.12 和独立虚拟环境。Windows PowerShell 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r scripts/requirements.txt
.\.venv\Scripts\python.exe scripts/demo_model.py --out outputs/demo-plate
.\.venv\Scripts\python.exe scripts/demo_model.py --out outputs/demo-assembly --assembly
```

macOS / Linux 示例：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python scripts/demo_model.py --out outputs/demo-plate
.venv/bin/python scripts/demo_model.py --out outputs/demo-assembly --assembly
```

示例生成 STEP、GLB、预览 PNG 和校验 JSON。导出工具会拒绝覆盖已有同名文件；重新运行时选择新目录或文件名。

自定义模型调用 `scripts/cad_export.py` 的 `Part` 和 `export_model`。输入为已经建立的 OCP 实体，单位为 mm；具体调用方式见 [SKILL.md](SKILL.md) 和 [demo_model.py](scripts/demo_model.py)。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 技能入口与完整工作流程 |
| [agents/openai.yaml](agents/openai.yaml) | 技能界面名称和默认提示 |
| [references/ocp-workflow.md](references/ocp-workflow.md) | CAD 建模方式、绑定差异和精度处理 |
| [references/session-examples.md](references/session-examples.md) | 吊板挂扣与安全立柱的参数案例、尺寸冲突处理 |
| [scripts/cad_export.py](scripts/cad_export.py) | 通用 STEP / GLB 导出、校验及预览工具 |
| [scripts/demo_model.py](scripts/demo_model.py) | 可运行的单零件与装配体示例 |
| [scripts/requirements.txt](scripts/requirements.txt) | 已验证环境的依赖版本 |

## 验证范围

此版本已用单零件、双零件装配，以及一个13零件安全立柱模型检查导出与重新读取流程。

STEP 可导入精确实体及装配结构，但不包含 SolidWorks 原生草图、特征历史或配合。尚未在 SolidWorks 中实际打开验证。补足尺寸和简化螺纹需要在具体模型交付说明中列出；模型导出校验不等于承载或制造验证。
