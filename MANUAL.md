# Molecular Lab Suite V26.9-Preview-1 使用手册

Molecular Lab Suite（简称 MLS）是面向 Gaussian / ORCA 的桌面工作站：**建模 → 生成输入 → 解析输出 → 电子激发分析 → 高质量绘图**，全部在本机完成；也可连接 Linux 服务器做远程解析与任务提交。

---

## 1. 运行环境与安装

| 项目 | 说明 |
| --- | --- |
| 操作系统 | Windows 10 / 11 64 位 |
| 安装方式 | 免安装：解压 `MLS-V26.9-Preview-1-win-unpacked.zip`，双击 `Molecular Lab Suite.exe` |
| 首次启动 | 在软件根目录自动生成 `mls-plots.json`（绘图配置）与 `Mols\`（保存的 `.mls` 分子文件） |
| 用户数据 | `%APPDATA%\mls-desktop\`（启动日志 `mls-main.log`、界面设置等） |
| 卸载 | 关闭程序后直接删除整个目录即可，注册表里不写东西 |

外部程序（可选，用到分析与绘图时需要）：

| 程序 | 用途 | 说明 |
| --- | --- | --- |
| **Multiwfn** | 生成轨道 / NTO / 空穴-电子 cube，激发态分析 | 建议 2026.x |
| **VMD** | 渲染图片（内部调用同目录的 Tachyon） | 建议 1.9.3，`tachyon_WIN32.exe` 与 `vmd.exe` 同目录 |
| **formchk** | Gaussian 的 `.chk` → `.fchk` | 装了 Gaussian 就有 |

---


## 2. 先配置外部程序

点右上角 **外部程序**，分别填入 Multiwfn、VMD 所在目录（目录里含对应 exe 即可）；也可以把这些目录加入系统环境变量 `PATH`，程序会自动去找。配置解读取的是 `config.json` 与界面设置，随时可改。

- 每个程序下面会显示 **实际使用** 的 exe 路径；没检测到时会给出提示。
- **Multiwfn 引用确认**：首次调用 Multiwfn 前会整屏显示引用说明，确认后才能继续（可勾选「不再提示」）。请务必在论文中引用原文。

---

## 3. 各功能页

### 3.1 分子结构

- 打开 `.mls / .mol / .sdf / .xyz / .pdb / .smi / .gjf / .inp / .log / .out`；左侧可切换 **Mols 目录**（软件自带的分子库）。
- **2D 画布**：环模板放置、单击画布加原子、从原子拖动建键、改元素/键级/电荷、加/去显式氢。
- **3D 视图**：自动生成三维坐标（`embed3d`）、测量距离/角度/二面角。
- **化学数据**：分子式、分子量、精确质量、环/芳香环统计、Gasteiger 电荷、整体偶极、InChI/InChIKey；支持按名称 / CID / SMILES 从 PubChem 检索，以及 NIST WebBook 谱图外链。
- **保存**：`保存`（写入 Mols 目录）或 `另存到…`。
- **生成输入文件**：**不需要先保存 `.mls`** —— 点这个按钮会把画布/3D 视图里当前的分子（按「保存时加氢」设置补上显式氢）连同电荷、多重度一起带到「生成输入」页并立即生成；回到本页改了结构再点一次，输入页会重新载入新结构。

### 3.2 生成输入

- 左侧选分子文件 → 右栏设置任务：Gaussian（`%mem`、`%nprocshared`、关键词行、电荷/多重度）或 ORCA（`!` 行、`%maxcore`、`%tddft`、`dosoc`、`*xyz` 坐标块）。
- 从「分子结构」页带过来的分子（未保存的也算）会直接出现在左栏，并显示当前分子与原子数。
- `重新生成` 预览、`复制`、`保存为文件`（写出 `.gjf` / `.inp`）。

### 3.3 修改GJF

- 从 Gaussian `.log` 里提取末帧结构，改关键词/内存/核数/泛函/基组/文件名前缀后写出新的 `.gjf`。
- 支持本地与远程目录、批量转换与批量修改（勾选多个文件一次处理）。
- `填入参数栏` 会把当前文件的关键词解析成各个字段，改完 `保存并应用参数至当前文件`。

### 3.4 提取扫描

- 解析扫描任务输出，按扫描步拆分/合并结构，输出新的 `.gjf`；可勾选「添加 %mem / %nprocshared 行」。
- 支持「提取选中（n）」与「提取全部（n）」。

### 3.5 轨道能量

1. 右栏选目录 → `解析 / 重新解析`（本地或远程）。程序读 `.log/.out` 里的轨道能量与占据情况。
2. 中间列出 Alpha/Beta、占据/空、能量（Ha 与 eV），标出 **HOMO/LUMO**；可算指定两个轨道的能隙、`导出 Excel`。
3. 勾选轨道 → `生成 cub（n）` 调 Multiwfn 生成 cube → `绘制（VMD）` 出图。
4. 渲染风格可选 **艺术级（无阴影，默认）/ 艺术级（阴影着色）/ 标准**；等值面数值可改。渲染期间可以切到别的文件继续渲染，互不影响。



### 3.6 NTO 分析

1. 左栏选含激发态信息的输出文件（TD 任务）。
2. 中栏勾选要分析的激发态 → `开始 NTO 分析`。程序调 Multiwfn 做 NTO 分析，给出本征值（贡献）表与贡献最大的 NTO 对 cube。
3. `绘制（VMD）` 出图；图上会标注分子名、态标号、轨道序号与贡献值、振子强度。

### 3.7 电子空穴

1. 同样先选文件、勾选激发态 → `开始空穴-电子分析`。
2. 右栏选择要导出的图形数据：空穴分布、电子分布、空穴-电子重叠 Sr、密度差 CDD、Chole/Cele（平滑化）、跃迁密度。
3. 中栏给出定量指标：激发能、空穴/电子积分、Sr/Sm、D 指数、Δσ、H、t、HDI/EDI、偶极变化、空穴/电子质心等。
4. `绘制（VMD）` 一次画出单图与叠加图：**只有 Chole / Cele（含 Chole+Cele 叠加图）用半透明等值面**，其余（hole/electron/Sr/CDD/跃迁密度/Hole+Electron）保持不透明；电荷中心球只画在 Chole/Cele 上（紫=空穴，橙=电子）。
5. 透明度、质心球半径、等值面默认值都在 `mls-plots.json` 里改（见第 5 节）。

### 3.8 TD 信息 / SOC 数据 / 重组能

- **TD信息**：解析 TD 输出（激发能、振子强度等），支持多图层叠加对比、`导出 CSV / Excel`。
- **SOC数据**：解析 ORCA 的 SOC 输出，列出 SOC 矩阵（|Hso| cm⁻¹），同样支持多图层与导出。ORCA 输出里单重态与三重态各自从 1 编号，界面按 **S1…/T1…** 分开标号，提交给 Multiwfn 时用文件顺序号。
- **重组能**：本地解析 `.out` 与 HuangRhys 文件，或连接服务器提交 `nomap` 任务；结果可 `导出 Excel（所有解析结果）`。

  远程任务参数（按界面里填的值原样传给 `nomap.sh`）：

  | 参数 | 含义 | 默认值 |
  | --- | --- | --- |
  | `g` | 高斯泛函 | `b3lyp` |
  | `gb` | 高斯基组 | `6-31G(d,p)` |
  | `o` | ORCA 泛函 | `b3lyp/G` |
  | `ob` | ORCA 基组 | 留空（不传该参数） |
  | `root` | 激发态根号 | `1` |
  | `sm` | 自旋多重度 | `1` |
  | `c` | 电荷 | `0` |
  | `coord` | 坐标类型 | `INTERNAL` |

### 3.9 远程功能

点顶栏 **连接服务器**：填主机/IP、用户名、密码（可保存为预设，密码存在系统密钥链里）。连接后：

- **终端**：交互式 shell；**FTP**：上传/下载文件。
- 各解析页的「远程」模式可以直接选远程目录解析，程序把需要的文件缓存到本地临时目录再解析。
- 远程缓存里的同名波函数文件（`.fchk/.wfn/.wfx/.gbw` 等）会在需要时自动下载。

---

## 4. 产物目录与命名

所有产物都放在你指定的输出目录（默认与源文件同目录）下，按体系分子名建子目录，图片统一再放进 `PIC\`：

| 功能 | 目录 | 文件命名 |
| --- | --- | --- |
| 轨道图 | `<分子名>-Orbitals\` | `<分子名>-orb<序号>.cub` / `.png` |
| NTO | `<分子名>-NTOs\` | `<分子名>-S<态>-NTO<序号>-<H/E>-<贡献>.cub` |
| 空穴-电子 | `<分子名>-HoleElectron\` | `<分子名>-S<态>-<hole/electron/Sr/CDD/Chole/Cele/transition>.cub` |

同名文件会覆盖更新；渲染中间文件（`_mls_*`）会在成功后被清理，Multiwfn 的输入脚本 `_mls_*.txt` 会保留，方便你核对或手动复现。

---

## 5. 绘图配置 `mls-plots.json`

放在**软件根目录**（exe 同级），启动时自动生成，改完保存、下次绘制即生效（不用重启）。常用项：

| 配置项 | 作用 |
| --- | --- |
| `default_style` | 界面默认渲染风格：`art_noshadow`（无阴影，默认）/ `art`（带阴影）/ `standard` |
| `styles.<名>.vmd` | 该风格的 VMD 附加设定（碳色、材质、取景、光源等） |
| `styles.<名>.tachyon` | 该风格的 Tachyon 参数（`-mediumshade` 无阴影 / `-fullshade` 带阴影、采样数等） |
| `styles.<名>.size` | 该风格的默认分辨率 |
| `vmd_template` | 默认 VMD 脚本（`{cub} {scene} {w} {h} {iso}` 占位符） |
| `overlay_proc` | 叠加图 VMD 过程；`{sphere_radius} {opacity_single} {opacity_two}` 会被下面的值替换 |
| `multiwfn_template` | 默认 Multiwfn 输入脚本（末尾自动补 `0`、`q`） |
| `hole_electron.iso` | 电子空穴密度等值面默认值（默认 0.0005） |
| `hole_electron.material` | 透明图使用的材质（默认 `Translucent`） |
| `hole_electron.trans_mode` | 透明模式：`trans_vmd`（默认）/ `trans_raster3d` |
| `hole_electron.opacity_single` | 单张 Chole / Cele 图的不透明度（默认 0.3，越大越实） |
| `hole_electron.opacity_two` | Chole+Cele 叠加图的不透明度（默认 0.3） |
| `hole_electron.sphere_radius` | 电荷中心小球半径（默认 0.35） |

写坏了也不怕：解析失败时会退回内置默认值，界面照常可用。

---

## 6. 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| 提示没检测到 Multiwfn / VMD | 在右上角「外部程序」里填目录，或把程序目录加入系统环境变量 `PATH` |
| `forrtl: severe (24)/(59)` 或 Multiwfn 卡住 | 输入脚本与你的 Multiwfn 菜单不一致。展开「编辑脚本模板」按版本调整，末尾必须有返回主菜单 `0` 与退出 `q`（程序会自动补） |
| `No basis function information` | `.log` 缺少波函数信息：Gaussian 加 `pop=full`（或 `gfinput`、`IOp(3/33=1)`），ORCA 加 `%output Print[P_Basis] 2` 与 `Print[P_MOs] 1`；或改用 `.fch/.fchk/.wfn/.wfx/.molden/.gbw` |
| 只有 `.chk` | 用「用 formchk 转 .fchk」按钮（需要装了 Gaussian 的 formchk 在 PATH 里） |
| 绘图失败、没有图片 | 看右下角日志；确认 VMD 目录里有 `tachyon_WIN32.exe`，或把 VMD 目录加入 PATH |
| 图片看着太白/太透 | 改 `mls-plots.json`：`hole_electron.opacity_*`（透明度）、`overlay_proc` 里的 `ambient/diffuse`（发白程度） |
| 切回旧文件时图片恢复慢 | 图片以 base64 传给界面，越大的图解码越慢。程序已默认用缩略图显示、点开大图时才读原图；也可把 `styles.*.size` 调小 |
| 想换中文/英文 | 顶栏右侧的语言按钮；默认英文 |
| 想彻底重置设置 | 关闭程序，删除 `%APPDATA%\mls-desktop\` 与软件根目录的 `mls-plots.json`，重新启动即可 |

日志：界面右上角「日志」按钮，或 `%APPDATA%\mls-desktop\mls-main.log`（启动过程与后端输出，超过 1 MB 会自动重开）。

---

## 7. 缓存与数据存放

程序**退出时会自动清理纯缓存**（启动时还会再清一次，兜住上次异常退出/被强杀留下的），设置类文件一个都不动：

| 位置 | 内容 | 退出时 |
| --- | --- | --- |
| `%APPDATA%\mls-desktop\Cache`、`GPUCache`、`DawnCache`、`Code Cache` | 浏览器内核缓存（通常几 MB～几十 MB） | **清理**（个别被系统短暂占用的文件留到下次启动清掉） |
| `%APPDATA%\mls-desktop\cache` | 远程解析下载的文件缓存 | **清理** |
| `%LOCALAPPDATA%\mls-desktop\thumbs` | 界面上显示用的图片缩略图缓存（每张渲染图一个） | **清理** |
| `%APPDATA%\mls-desktop\mls-main.log` | 启动日志 | 保留（> 1 MB 自动重开） |
| `%APPDATA%\mls-desktop\Local Storage`、`Preferences`、`mls-preferences.json` | 界面设置、外部程序目录、主题、语言 | 保留 |
| `%APPDATA%\mls-desktop\.mls_key`、`presets.json` | 密码加密密钥、服务器预设 | 保留 |
| 软件根目录 `Mols\`、`mls-plots.json` | 你的分子文件与绘图配置 | 保留 |

清理只在退出/启动时进行，运行期间不动任何文件；想手动清一次，直接删上面标「清理」的那几项也可以，程序下次会重建。

---

## 8. 引用与致谢

- **Multiwfn**：使用其功能请引用 Tian Lu 的原文（程序内会整屏提示，请务必遵守）。
- 教程与参数来源：Sobereva 计算化学公社 —— 轨道图 <http://sobereva.com/447>、艺术级渲染 <http://sobereva.com/449>、NTO 分析 <http://sobereva.com/377>、空穴-电子分析 <http://sobereva.com/434>。
- **VMD / Tachyon**：University of Illinois，引用方式见其官方说明。

---

版本：**Molecular Lab Suite V26.9-Preview-1**
