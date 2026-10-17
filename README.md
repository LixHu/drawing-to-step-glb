# 图纸转 STEP 和 GLB

`drawing-to-step-glb` 是采用 [Agent Skills 开放格式](https://agentskills.io/specification)的通用技能：根据机械工程图、尺寸截图或草图建立参数化 CAD 实体，导出 SolidWorks 可导入的 STEP，以及从同一实体生成的 GLB。

识图和建模由使用技能的智能体完成，附带的 Python 工具负责实体导出、重新读取校验和几何预览。它不是无需核对尺寸的一键图片转换器。

核心流程和 Python 脚本不依赖特定模型厂商。支持标准技能格式，并具备图纸读取、文件操作和终端/Python执行能力的 Agent，可以使用同一套技能文件。

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

仓库地址：[LixHu/drawing-to-step-glb](https://github.com/LixHu/drawing-to-step-glb)。

使用 [Skills CLI](https://github.com/vercel-labs/skills)，在已安装 Node.js / npm 的电脑上执行：

```bash
npx skills add https://github.com/LixHu/drawing-to-step-glb --skill drawing-to-step-glb -g
```

`-g` 表示安装到用户范围。安装器会检测 Agent 环境，支持交互选择目标。也可一次安装到安装器支持的全部 Agent（目标还需支持用户范围安装）：

```bash
npx skills add https://github.com/LixHu/drawing-to-step-glb --skill drawing-to-step-glb -g --agent '*'
```

### 指定 Agent 安装

在上面命令末尾加 `-a <agent-id>` 即可指定工具；也可以在一个 `-a` 后列出多个ID，例如：

```bash
npx skills add https://github.com/LixHu/drawing-to-step-glb --skill drawing-to-step-glb -g -a claude-code cursor opencode gemini-cli github-copilot codex
```

| 工具 | Agent ID |
| --- | --- |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| OpenCode | `opencode` |
| Gemini CLI | `gemini-cli` |
| GitHub Copilot | `github-copilot` |
| Windsurf | `windsurf` |
| Cline | `cline` |
| Roo Code | `roo` |
| Trae | `trae` |
| Qwen Code | `qwen-code` |
| Codex | `codex` |

更多工具及最新安装目录见 [Skills CLI 支持列表](https://github.com/vercel-labs/skills#supported-agents)。安装目录由安装器适配，不需要为每个工具维护一套重复技能。已有同名技能时，按实际需要保留或更新原版本。

在线安装负责安装技能文件；首次建模时，智能体会按技能要求检测 CAD 环境并按需准备独立 Python 依赖。

### 调用技能

安装完成后，在所用 Agent 中附上图纸，通过技能菜单、宿主支持的快捷命令或明确提及技能名称来调用，例如：

```text
使用 drawing-to-step-glb 技能，根据这张图生成 STEP 和 GLB。
保留原有模型；尺寸冲突先说明，缺失尺寸列为补足项。
```

圆管建议同时提供外径、壁厚和管长，并注明长度指管长还是装配总高。总装图和零件详图一起提供时，可以更准确地确定连接结构。

### 本地开发安装

开发或离线调试时，也可以将本仓库复制到目标工具支持的技能目录，目录名保持为 `drawing-to-step-glb`。各工具的目录见安装器支持列表，文件结构一致：

```text
drawing-to-step-glb/
├── SKILL.md
├── agents/openai.yaml    # 可选的 Codex 界面元数据
├── references/
└── scripts/
```

`agents/openai.yaml` 仅为 Codex 提供名称和默认提示等界面元数据，其他 Agent 可忽略；它不控制核心建模能力，也不要求使用 OpenAI API。标准入口是根目录的 `SKILL.md`，脚本可以独立运行。

### 兼容范围

安装器支持某个工具，表示能把技能安装到该工具的约定目录；不代表已经在所有工具中实测建模。完整工作流要求图像读取、终端执行、文件读写，以及可用的 Python 3.12 / CAD依赖。支持 Windows、macOS、Linux 的环境准备写法；实际运行还取决于平台有可用的 OCP 依赖包。

不原生读取 `SKILL.md` 的 Agent，如果允许加载本地说明并执行Python，也可让它读取本技能入口及相关参考文件。仅聊天、不能执行代码的环境，可以协助解释图纸或输出脚本，不能承诺完成文件生成和校验。

## 开发者：单独运行 Python 导出工具

获取源码：

```bash
git clone https://github.com/LixHu/drawing-to-step-glb.git
cd drawing-to-step-glb
```

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

复用独立依赖缓存时可设置 `DRAWING_CAD_PACKAGES`；预览字体可通过 `DRAWING_CAD_FONT` 指定，未指定时自动尝试常见字体并回退到内置字体。使用标准虚拟环境时无需设置这两个变量。

## 文件说明

| 文件 | 用途 |
| --- | --- |
| [SKILL.md](SKILL.md) | 技能入口与完整工作流程 |
| [agents/openai.yaml](agents/openai.yaml) | Codex 可选界面元数据，其他工具可忽略 |
| [references/ocp-workflow.md](references/ocp-workflow.md) | CAD 建模方式、绑定差异和精度处理 |
| [references/session-examples.md](references/session-examples.md) | 吊板挂扣与安全立柱的参数案例、尺寸冲突处理 |
| [scripts/cad_export.py](scripts/cad_export.py) | 通用 STEP / GLB 导出、校验及预览工具 |
| [scripts/demo_model.py](scripts/demo_model.py) | 可运行的单零件与装配体示例 |
| [scripts/requirements.txt](scripts/requirements.txt) | 已验证环境的依赖版本 |

## 验证范围

此版本已用单零件、双零件装配，以及一个13零件安全立柱模型检查导出与重新读取流程。

已在独立临时项目中使用 Skills CLI，对 Claude Code、Cursor、OpenCode、Gemini CLI、GitHub Copilot、Windsurf、Cline、Codex 八个目标完成安装分发检查，确认技能说明、脚本和参考资料随技能一起安装。共用标准技能目录的工具共用安装位置。

多 Agent 兼容性以标准格式、无厂商专用执行依赖和安装分发为基础；未逐一在每个 Agent 的会话中运行 CAD任务，也未在 macOS / Linux 上实测运行。

STEP 可导入精确实体及装配结构，但不包含 SolidWorks 原生草图、特征历史或配合。尚未在 SolidWorks 中实际打开验证。补足尺寸和简化螺纹需要在具体模型交付说明中列出；模型导出校验不等于承载或制造验证。
