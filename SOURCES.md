# SOURCES.md · 太阳系八大行星动态运转 3D 作品

- 生成日期：2026-11-06；最后修订：2026-11-07（**兼容加固 v1.2**：IIFE 全局包去 importmap/ESM、WebGL 静态降级、og 分享元信息与预览图、发布就绪包；**v1.3**：真机反馈暴露的 `OrbitControls` 符号引用缺陷修复、运行时冒烟测试、修复版重新发布与线上 23/23 复核；物理与数值全程未改动）
- 精度等级：**教学／科普级「物理可核验」** —— 不是艺术动画，也不是航天级星历
- 交付物：**`太阳系八大行星动态运转.html`**（中文主文件，内置数值自检面板与 16 组误差表）、`index.html`（薄重定向 + 完整 og 元信息）、`assets/preview.png`（1200×630 分享卡片图）、`vendor/`（Three.js r160 ESM 原件 + 由其确定性生成的 `three.iife.js` 全局包 + OrbitControls + MIT 许可证）、`build/`（IIFE 构建、预览图生成、发布目录生成、基址替换、HTTP 验收脚本）、`publish/`（GitHub Pages 干净发布版）、`README.md`、`verify.mjs`（独立校验）、`reference_ephem.py`（参照数据生成器）、`reference.json`（golden file）、`sync_reference.py`（内联快照同步）、`verify_page.py`（页面↔命令行一致性）、`verify_compat.py`（兼容加固 8 项验收）、本文件
- 规格依据：提示词 V1（网页可交互路线），见 `../01_方法论沉淀/四问框架与两版提示词_v1.0_20261106.md` §4

---

## 1. 一手数据源逐项登记

| 数据 | 来源 | 历元／版本 | 检索日期 | 授权／credit |
|---|---|---|---|---|
| 六根数 a, e, I, L, ϖ, Ω 及世纪变率（1800–2050 AD） | E. M. Standish, *Keplerian Elements for Approximate Positions of the Major Planets*, JPL Solar System Dynamics `https://ssd.jpl.nasa.gov/planets/approx_pos.html` | J2000.0，变率为每儒略世纪；适用 1800–2050 AD | 2026-11-06 | NASA/JPL 公开技术资料；引用 Standish [Sta92, Sta21] |
| 长时段表（3000 BC–3000 AD）与 M 的附加项 b/c/s/f | 同上，JPL 页面第二张表 | 同上 | 2026-11-06 | 同上 |
| 自转周期、轴倾角、直径、轨道周期 | NASA/NSSDCA *Planetary Fact Sheet - Metric* `https://nssdc.gsfc.nasa.gov/planetary/factsheet/` | Last Updated 18 March 2025, DRW | 2026-11-06 | Author/Curator: Dr. David R. Williams, NSSDCA / NASA Goddard Space Flight Center |
| **第三方参照星历（判卷用）** | **PyEphem 4.2.1 / libastro (XEphem) 的 VSOP87 解析行星理论**，`https://pypi.org/project/ephem/`，本机由 PyPI 预编译 wheel 安装 | ephem==4.2.1 (cp313 macOS arm64) | 2026-11-06 | **仅用其输出的参照数值**；未把第三方代码、二进制或星历文件打包进作品。具体许可证未在本会话核实，故不作授权声明；重新生成参照值的命令见 §6 |
| 开普勒方程与黄道旋转公式 | Standish 原文 + 两处独立实现交叉核对 | — | 2026-11-06 | 见下 §2 |
| 黄经总岁差多项式 p(T) | Meeus, *Astronomical Algorithms* 通用岁差多项式 | J2000 起算 | 2026-11-06 | 见 §4.2；本会话未在线复核原书，按公开通用式写明，可由两时刻误差自证 |
| AU = 149 597 870.7 km | IAU 2012 Resolution B2 / JPL SSD 常数页 | 定义值 | 2026-11-06 | 国际天文学联合会 |
| J2000.0 = JD 2451545.0 (TDB) | IAU 标准历元 | 定义值 | 2026-11-06 | 国际天文学联合会 |
| UTC→TDB = 32.184 s + 37 闰秒 | TT−TAI 定义值 + IERS 闰秒表 | 37 s 自 2017-01-01 起未增加 | 2026-11-06 | **未在本次会话在线复核**，列为待核实项 |
| **渲染依赖资产** | Three.js `three@0.160.0` 的 `build/three.module.js`（1 272 972 B）与 `examples/jsm/controls/OrbitControls.js`（29 868 B），自官方备用节点 `https://fastly.jsdelivr.net/npm/three@0.160.0/` 下载后随作品落盘 | 0.160.0，文件头标注 `@license ... SPDX-License-Identifier: MIT` | 2026-11-07 | **MIT**，许可证全文随附 `vendor/THREE-LICENSE.txt`；主文件无外部 import，OrbitControls 仅 `from 'three'`，由本地 importmap 解析 |

### §1.1 关于 JPL 原页与 Horizons 不可达的如实说明

本会话所在网络**能正常访问一般网站**（`example.com`、`www.nasa.gov` 均 HTTP 200），但 `ssd.jpl.nasa.gov` 返回 **HTTP 000**（代理 `CONNECT tunnel failed 502`／直连超时）；`naif.jpl.nasa.gov` 同样超时；网页抓取与文本镜像通道也失败。备用域 `ssd-api.jpl.nasa.gov` 可达，但其官方文档 `doc/horizons.html` 明确列出**唯一数据端点仍是 `ssd.jpl.nasa.gov/api/horizons.api`**，该备用域的 `/api/horizons.api` 与 `/horizons.api` 均返回 404，只提供文档、不提供数据。

因此**本作品没有声称「数值直接下载自 JPL 原页」**，也没有声称 Horizons 在线对照已完成。实际做法是把 JPL 表在三处公开转载间交叉核对，逐位一致后使用：

另注：本会话 `cdn.jsdelivr.net` 同样不可达（SSL HTTP 000），曾短暂改用官方备用节点 `fastly.jsdelivr.net`；2026-11-07 先把两个 JS 文件下载到 `vendor/` 改为本地 importmap（§4.4），随后又打成单文件 IIFE 全局包、彻底去掉 importmap 与 ESM（§4.5）。**页面运行时不发起任何外网请求，且可直接双击 `file://` 打开**。数值自检面板与 3D 层解耦，不受影响。

1. `http://www.rschr.de/PRPDF/aprx_pos_planets.pdf` — Standish 原文 PDF 转载，含 1800–2050 完整表格
2. `https://www.danbp.org/h/posts/planet-position-calculator-javascript` — 基于 Standish 论文的 JS 实现，含两张完整表与全部公式
3. `https://orbital-mechanics.space/reference/planetary-ephemeris.html` — 明确标注 "Reproduced from Standish [Sta92, Sta21]"，给水星行与完整计算步骤

另经 GitHub 代码检索命中多个独立实现（`NCAR/DART`、`esa/jupiter_tour`、`eteq/astropysics` 等）作为存在性佐证。三处数值逐位一致（例如水星 `0.38709927 / 0.20563593 / 7.00497902 / 252.25032350 / 77.45779628 / 48.33076593` 与 `149472.67411175`）。

### §1.2 一个与 V1 提示词不一致、必须声明的发现

V1 §2 要求「M = L − ϖ（**含 JPL 表的 bT² 与周期项**）」。核实结果：

- **1800–2050 AD 表的 b/c/s/f 全部为 0**，即 `M = L − ϖ`；
- `b·T² + c·cos(fT) + s·sin(fT)` 属于 **3000 BC–3000 AD 长时段表**，且仅木星至冥王星非零。

处理：`太阳系八大行星动态运转.html` 内置**两套完整表**，`CONFIG.ELEMENT_SET` 默认 `1800-2050`（两个检验时刻 2000/2026 均在其适用区间内，精度更高）；`M` 的公式按 Standish 原式完整写入，短表时附加项自动为 0。切换到长表即启用 `bT² + 周期项`。这是按核实结果做的修正，不是静默漏实现。

### §1.3 精度上限声明（部分未取得）

V1 要求「引用 JPL 页面自带精度表声明误差上限」。**本会话未能取得该精度表原值**（原因见 §1.1），因此**不编造、不引用**任何角秒数值。替代证据链（已落地）：

- **默认对照**：`node verify.mjs` 读取 `reference.json`，与 PyEphem/VSOP87 独立星历逐项比对，教学级阈值 `|Δ黄经| < 1°`，16/16 全部 PASS（见 §4.2）；
- **可选取证**：`node verify.mjs --online` 在能访问 `ssd.jpl.nasa.gov` 且响应含 `$$SOE` 块时改与 Horizons 对照；本会话预检不通过，脚本明确报出"目标域名不可达"并降级回本地参照；
- 公开转载对 Standish 公式精度的定性表述为「误差可达数千公里量级」；
- 本作品所有自检结果与两个时刻的位置表见 §4，可独立重跑。

---

## 2. 物理与数学实现对照

| V1 要求 | 实现 | 状态 |
|---|---|---|
| UTC → JD → TDB；T=(JD−2451545.0)/36525 | `jdUTC` / `jdTDB`，TDB ≈ TT = UTC + 32.184 s + 37 s | 已实现（闰秒简化，见 §5） |
| 根数线性外推 a=a₀+ȧT | `elementsAt()` | 已实现 |
| ω=ϖ−Ω；M=L−ϖ（含附加项） | `stateOf()` | 已实现 |
| 牛顿迭代解 M=E−e*·sinE，tol 1e-6° | `solveKepler()`，实测 2–3 次收敛，残差 ≤ 8.5e-7° | 已实现 |
| x'=a(cosE−e), y'=a√(1−e²)sinE；旋转到 J2000 黄道 | `eclFromE()`，标准 Rz(Ω)Rx(I)Rz(ω) 展开式（等价于 V1 写法） | 已实现 |
| 近日点快、远日点慢可见 | 真椭圆 + 开普勒方程；自检②量化验证 | 已实现 |
| 自转 W=W₀+W′·d、公转自转独立计时 | `mesh.rotation.y = (d·360/|P|)°`，d 为 TDB 天数 | 部分实现（见 §5 取舍） |
| delta-time 累积、暂停／倍率／跳转／回 J2000 | `frame()` 用 `dt` 累积 `simMs`；HUD 提供全部控件 | 已实现 |
| 双尺度 + HUD 公式 + 观赏／真实切换 | 见 §3 | 已实现 |
| PBR、点光源、昼夜分界、土星环缝、月球、星空 | MeshStandardMaterial + PointLight + 程序化环／纹理／星点 | 已实现（非真实影像） |
| 轨道线按真实偏心率 | 每条轨道按 E 采样 360 点生成真实椭圆后整体缩放 | 已实现 |
| 相机、点击信息卡、跟随、时间轴、开关 | OrbitControls + Raycaster + HUD | 已实现 |
| DPR 限制、纹理分级、减少动效默认静态、移动端 | `DPR_MAX=1.75`、canvas 程序化纹理、`prefers-reduced-motion` 默认暂停、响应式 CSS | 已实现（instancing 未使用，见 §5） |
| 页面内置自检面板显示 16 组第三方星历误差表 | 普通脚本内联 `REFERENCE` 快照 + `comparisonTable()` 用同一套 `stateOf()` **现场重算**，含岁差修正前／后对比、时标对齐与总览判定 | 已实现，见 §4.3（不依赖 CDN） |

---

## 3. 尺度策略（显式声明，禁止宣称「完全按比例」）

真实比例下地球直径 ≈ 1.276×10⁴ km，海王星轨道半径 ≈ 4.5×10⁹ km，比值约 **2.8×10⁻⁶**；在 60 单位/AU 下地球直径仅 0.0026 单位，远小于 1 像素。

| 项 | 公式 | 单位 |
|---|---|---|
| 轨道距离（观赏） | `R(a) = 10 + 55·log10(1 + a/0.15)`，a 为 AU | 场景单位 |
| 轨道形状 | 每颗轨道按 `R(a)/a` **等比例缩放**真实椭圆 → 偏心率、倾角、近日点方向完整保留，不是圆 | — |
| 天体半径（观赏） | `r(D) = 0.55 + 3.2·(D/70000)^0.42`，D 为直径 km | 场景单位 |
| 真实比例 | `60 单位/AU`，距离与半径同一尺度 | 场景单位 |

切到真实比例时球体隐藏、退化为固定大小标记点 + 标签（HUD 已注明属预期行为）。两套公式均在页面左下角图例写死，可核对。

---

## 4. 数值自检结果（`node verify.mjs`，2026-11-06 实跑）

两个检验时刻：

- `2000-01-01 12:00 TDB` → JD(TDB) = 2451545.000000
- `2026-01-01 00:00 UTC` → JD(TDB) = 2461041.500801

| 行星 | 2000 黄经(°) | 2000 日距(AU) | 2026 黄经(°) | 2026 日距(AU) |
|---|---:|---:|---:|---:|
| 水星 | 253.7837 | 0.466475 | 242.2608 | 0.462548 |
| 金星 | 182.6070 | 0.720229 | 277.0210 | 0.727357 |
| 地球 | 100.3802 | 0.983307 | 100.2095 | 0.983324 |
| 火星 | 359.4483 | 1.391159 | 283.7949 | 1.428952 |
| 木星 | 36.3804 | 4.967306 | 108.9668 | 5.209075 |
| 土星 | 45.5786 | 9.172322 | 1.6270 | 9.516355 |
| 天王星 | 316.3990 | 19.921688 | 59.5435 | 19.483463 |
| 海王星 | 303.9164 | 30.117301 | 0.9857 | 29.882454 |

1. **开普勒第三定律** T²/a³：T 取自 NASA Fact Sheet **独立周期**（不由 a 反算，避免自证）。最大偏差 **0.014152**（海王星，因 Fact Sheet 周期只给到整数天）→ **PASS**（教学级阈值 0.02）。
2. **面积速度**：水星近日点 1.55082°/日 > 远日点 0.67327°/日；火星 1.21131°/日 > 0.83281°/日 → **PASS**。
3. **自转对照**：金星 −5832.5 h / 177.4°，天王星 −17.2 h / 97.8°，逆行与大倾角均已施加 → **PASS**。
4. **开普勒迭代**：水星两时刻均 3 次收敛，残差 2.36e-14° / 2.86e-11° → **PASS**。
5. **离线自检总体：PASS**。
6. **第三方星历逐项误差表：已完成，16/16 PASS**（见 §4.2），不再是 SKIP。

> 首轮自检曾出现面积速度 FAIL，定位为脚本 bug：`atan` 在真近点角跨 180° 时分支跳变产生 359° 假位移。已加入角度归一化与最小角差计算后复跑 PASS。此处如实记录，避免把「修过了」当成「本来就对」。

### §4.2 第三方星历对照：判据替换与方法

**为什么替换**：V1 §5 要求「与 JPL Horizons 同刻输出逐项对比」。该端点在本会话网络不可达（§1.1），若坚持原判据就只能交 SKIP。按 Q4「谁来判卷」的原则，处理方式是**换一个同等独立、且本机可复现的判卷人**，并公开声明替换，而不是降低要求或假装完成。

**替换后的判卷人**：PyEphem 4.2.1 / VSOP87 解析行星理论。它与 JPL DE 数值积分星历在**理论、数据源、实现代码**上均不同，因此比对不是自证；独立性甚至强于"用同一套 DE 星历的不同接口"。参照值由 `reference_ephem.py` 生成并固化为 `reference.json`（golden file），`verify.mjs` 只读该文件——**运行校验不需要 Python、不需要网络、不需要安装任何包**。

**坐标系对齐（最易出错、必须写明）**：PyEphem 的 `hlong` 是**当日黄道／当日春分点**下的日心黄经，而本模型输出 **J2000 黄道系**。两者相差黄经总岁差：

```
p(角秒) = 5028.796195·T + 1.1054348·T² + 0.00007964·T³ − 0.000023857·T⁴
T = (JD_TDB − 2451545.0)/36525
lon_J2000 = (lon_date − p/3600) mod 360
```

实测 `p(2000) ≈ 0°`、`p(2026) = 0.363212°`。**不修正时 2026 时刻八颗行星全部呈现约 0.36° 的系统偏差**；扣除后回落到 0.0003°–0.0738°，证明修正方向正确（这本身是一条可证伪的自检）。该式是黄经岁差一阶近似，忽略黄道面自身旋转、章动与光行差，估计残差 < 0.01°，远小于 1° 阈值。

八颗行星取同一路径：七颗用各自 `body.hlong` / `sun_distance`；PyEphem 无 `Earth` 类，地球改用 `Sun().hlong`（即地球日心黄经，已实测与 `Ecliptic(Sun, epoch=date).lon − 180` 一致）与 `Sun.earth_distance`。时间口径：本模型 `TDB = UTC + 69.184 s`，故 `2000-01-01 12:00 TDB` 对应 PyEphem 输入 `2000/01/01 11:58:56.816 UTC`，`2026-01-01 00:00 UTC` 直接输入；两者为同一物理瞬间。

**实跑误差表**（`node verify.mjs`，2026-11-06）：

| 时刻 | 行星 | 本模型° | 参照° | \|Δ黄经\|° | \|Δr\| AU | 判定 |
|---|---|---:|---:|---:|---:|---|
| 2000 | 水星 | 253.7837 | 253.7830 | 0.0007 | 0.000003 | PASS |
| 2000 | 金星 | 182.6070 | 182.6029 | 0.0041 | 0.000017 | PASS |
| 2000 | 地球 | 100.3802 | 100.3778 | 0.0023 | 0.000020 | PASS |
| 2000 | 火星 | 359.4483 | 359.4474 | 0.0009 | 0.000049 | PASS |
| 2000 | 木星 | 36.3804 | 36.2946 | 0.0858 | 0.001925 | PASS |
| 2000 | 土星 | 45.5786 | 45.7223 | **0.1437** | 0.011523 | PASS |
| 2000 | 天王星 | 316.3990 | 316.4187 | 0.0197 | 0.002360 | PASS |
| 2000 | 海王星 | 303.9164 | 303.9291 | 0.0127 | 0.003222 | PASS |
| 2026 | 水星 | 242.2608 | 242.2626 | 0.0017 | 0.000002 | PASS |
| 2026 | 金星 | 277.0210 | 277.0213 | 0.0003 | 0.000013 | PASS |
| 2026 | 地球 | 100.2095 | 100.2097 | 0.0003 | 0.000003 | PASS |
| 2026 | 火星 | 283.7949 | 283.7967 | 0.0017 | 0.000259 | PASS |
| 2026 | 木星 | 108.9668 | 108.9674 | 0.0007 | 0.002819 | PASS |
| 2026 | 土星 | 1.6270 | 1.5531 | 0.0738 | 0.002186 | PASS |
| 2026 | 天王星 | 59.5435 | 59.5393 | 0.0041 | 0.006698 | PASS |
| 2026 | 海王星 | 0.9857 | 0.9957 | 0.0101 | 0.002304 | PASS |

**结论：16/16 通过，最大 \|Δ黄经\| = 0.1437°（2000 时刻土星），远小于 1° 阈值；含第三方对照总体 PASS。** 木星／土星在 2000 时刻的百分之一度级偏差与 Standish 短表（忽略摄动）的已知量级一致，属预期而非错误。

### §4.3 页面内置自检面板（16 组误差表现场重算）

**为什么不是静态贴表**：把误差表硬编码进 HTML 等于把判卷结果写死，第三方无法复核。页面做法是——把 `reference.json` 的 16 组参照值作为**数值快照**内联（`/* ---REF-BEGIN--- */` 段），再用与 3D 场景**同一套** `stateOf()` / `angDiff()` / `jdTDB()` 现场重算 `|Δ黄经|`、`|Δr|` 与 PASS／FAIL。参照值是数据，误差是算出来的。

**解耦**：纯数值层与自检面板放在普通 `<script>` 中，通过 `window.SOLAR` 把同一套函数交给 3D 层普通脚本使用。因此 **即便 3D 层加载失败，自检面板仍照常显示**。2026-11-07 起 Three.js 已本地化并 IIFE 化（§4.4、§4.5），此解耦继续作为防御性设计保留；另新增独立降级层，WebGL 不可用时仍显示静态视图与同一张误差表（§4.5）。

**面板新增的可证伪项**：

| 项 | 页面现场计算 | 结果 |
|---|---|---|
| 16 组误差明细 | 两时刻分组表，列本模型°／参照°／\|Δ经\|°／\|Δr\|AU／判定 | 16/16 PASS，最大 0.1437° |
| 参考系对齐 | 2026 时刻用未修正 `lonDate` 与修正后 `lonJ2000` 各算一次平均误差 | 修正前 0.3553° → 修正后 0.0116° |
| 时标对齐 | 页面 `jdTDB` 与 golden file `jdTDB` 的 ΔJD | 两时刻均 0.0e+00（阈值 < 1e-4） |
| 总览条 | `⑤ 独立第三方星历对照：16/16 PASS` + 判卷人版本与阈值 | 与 `node verify.mjs` 一致 |

**一致性验证（可复跑）**：`python3 verify_page.py` 抽取页面普通脚本、在 Node 里用 DOM stub 执行，与 `node verify.mjs --json` 的 16 行逐项比对。实跑结果：内联参照与 `reference.json` **逐位一致**（2 时刻 × 8 行星 × 4 类数值），16 行 `dLon`／`dR`／`pass` **最大差 0.00e+00**，总体判定一致 PASS；两份脚本语法检查通过。执行中曾抓到并修复一处真 bug——内联字段名 `n` 与比对函数读取的 `r.name` 不一致，导致行星名为 `undefined`；这正是"现场重算"而非贴表才能暴露的问题。

**副本同步风险**：内联值是 golden file 的副本。若重跑 `reference_ephem.py` 生成新参照，必须紧接着运行 `python3 sync_reference.py`（按 REF 标记重建内联块，实测幂等），再跑 `verify_page.py` 复核；否则会出现"页面与命令行结论分叉"。这是"页面零外部请求可核验"约束下的已知取舍，见 §5 #11。

### §4.4 中文主文件名与彻底离线（2026-11-07）

**问题**：页面 `<title>` 与 HUD 标题本来就是中文（"太阳系八大行星动态运转"），但**文件名是 `index.html`**，在文件卡片、目录与分享链接里显示英文，不易识别。

**处理**：主文件重命名为 **`太阳系八大行星动态运转.html`**，内容保持为唯一事实来源；`index.html` 改为 1.2 KB 的薄重定向页（含中文标题、可点链接、URL 编码跳转），保证静态服务根路径 `http://localhost:8811/` 与既有链接仍可用，**不产生第二份内容副本**。`sync_reference.py`／`verify_page.py`／`verify.mjs` 的文件名引用已同步到中文主文件。

**彻底离线**：把 Three.js 0.160.0 的两个 ESM 文件与 MIT 许可证下载到 `vendor/`：

| 文件 | 字节 | 来源 | 校验 |
|---|---:|---|---|
| `vendor/three.module.js` | 1 272 972 | `fastly.jsdelivr.net/npm/three@0.160.0/build/three.module.js` | 文件头 `@license ... MIT`；全文无 `import` 语句 |
| `vendor/addons/controls/OrbitControls.js` | 29 868 | 同版本 `examples/jsm/controls/OrbitControls.js` | 仅 `from 'three'`；现仅作 ESM 原件保留，运行时改用 IIFE 包 |
| `vendor/THREE-LICENSE.txt` | 1 081 | 同版本 `LICENSE` | MIT 全文 |

当时 importmap 改为 `{"three":"./vendor/three.module.js","three/addons/":"./vendor/addons/"}`，**页面外网 URL 数为 0**；`python3 -m http.server 8811` 下逐项 HTTP 验收：`/`、`index.html`、中文主文件（URL 编码）、两个 JS、许可证、`reference.json`、`verify.mjs`、`SOURCES.md` 全部 **200**、MIME 正确、字节哈希与本地文件一致。

**当时的限制（已在 §4.5 消除）**：ESM 模块在 `file://` 下被浏览器 CORS 策略阻止，因此"离线"只等于"不需要外网"，不等于"双击文件即可运行"；仍须本地静态服务。数值自检面板由普通脚本运行，连静态服务都不依赖。

**验收后复跑**：`python3 sync_reference.py`（幂等）、`python3 verify_page.py`（16 行逐位一致，最大差 0.00e+00）、`node verify.mjs`（离线总体 PASS + 含第三方对照总体 PASS），结论与改造前完全一致 —— 物理与数值未改动。

---

### §4.5 兼容加固 v1.2：IIFE 去 importmap + WebGL 降级 + og 元信息（2026-11-07）

**触发**：作品要发到 GitHub Pages 并分享到微信／小红书，而微信内置内核对 importmap 支持不确定、部分设备禁 WebGL、分享卡片需要服务端可抓取的绝对 URL。三项都属「载体绑定的约束」，按四问框架 Q1 必须在交付前补齐，且不得改动物理与数值。

**① IIFE 全局包（去 importmap / 去 ESM）**

零依赖脚本 `build/build_iife.py` 只做三处机械改写，库代码本身逐字保留：

| 改写 | 位置 | 结果 |
|---|---|---|
| `export { ... }` | `three.module.js` 末尾唯一一处（416 个导出名） | `window.THREE = { ... }` |
| `import { ... } from 'three'` | `OrbitControls.js` 顶部（10 个名字） | `const { ... } = window.THREE` |
| `export { OrbitControls }` | `OrbitControls.js` 末尾 | `window.THREE.OrbitControls = OrbitControls` |

两段各自包进 IIFE 并显式 `"use strict"`（ESM 默认严格模式）。产物 `vendor/three.iife.js` **1 304 274 字节**，不压缩、便于第三方逐字审计；源文件 sha256 前 16 位写入产物头注释。主页面改为普通 `<script src="./vendor/three.iife.js">`，3D 层也由 `<script type="module">` 改为普通 `<script>` 并包进 IIFE。

验收：`node --check vendor/three.iife.js`；`node build/verify_bundle.mjs` → 416 个源导出全部存在 + OrbitControls = 417 键、r160、无 ESM 残留、无 `import.meta`、无外链、Vector3/Color 冒烟通过。**副产品：现在可直接双击 `file://` 打开，不再需要静态服务**；静态服务与 GitHub Pages 仍兼容。

**② WebGL 降级（不白屏）**

- `<head>` 先跑探测脚本：依次尝试 `webgl2 / webgl / experimental-webgl`，成功后立即用 `WEBGL_lose_context` 释放临时上下文，结果写入 `window.__WEBGL__`。
- 3D 层在初始化前检查 `probe.ok` 与 `window.THREE` 完整性；失败即调用独立的 `window.__SOLAR_FALLBACK__()`。
- 降级渲染器是**第三段普通脚本**，完全不依赖 THREE：用 `window.SOLAR.stateOf()` 现场计算 J2000 时刻八大行星日心黄经与日距，画成内联 SVG（轨道半径 `R(a)`、行星位置半径 `R(r)`），并把 `16/16 PASS` 结论写入视图。CSS 用 `body.fb-on` 隐藏 3D 控件、把自检面板改为可滚动的常规面板（含移动端覆盖规则）。
- 初始化异常、首帧渲染异常、`webglcontextlost` 都走同一降级路径；12 秒超时提示在降级激活后不再误报。

验收：`verify_compat.py` 第 6 项用 DOM stub 在 Node 里模拟「WebGL 被禁用」，端到端执行数值层 + 降级层 + 3D 层，断言 3D 层提前返回、`fb-on` 生效、SVG 含 18 个圆与全部中文行星名、`16/16 PASS` 仍可见。**这是静态 + stub 验收，不能替代真实手机微信内核的端到端渲染确认**。

**③ og 分享元信息与预览图**

- 主文件与 `index.html` 均带 `og:type / site_name / title / description / url / image / image:width / image:height / image:alt`、`twitter:card / title / description / image`、`description`、`theme-color`、`canonical`；两页 url/image/title/description 由 `verify_compat.py` 逐项比对一致。
- `og:image` 指向 `https://zgch028.github.io/solar-system-3d/assets/preview.png`（1200×630 PNG，143 153 字节）。该绝对 URL **仅由分享平台爬虫在服务端读取，页面运行时不会请求**；`<script src>` 与样式表引用中运行时外链数仍为 0。仓库改名用 `python3 build/set_pages_base.py <repo> [owner]` 幂等批量替换。
- 预览图由 `build/make_preview.py` 读取 golden file `reference.json` 的 J2000 历元生成：轨道圆取 JPL 1800–2050 表半长轴 a、行星点取参照星历当前日距 r，与页面降级图同口径；背景星点固定种子 20261106，程序化生成、非真实影像。
- 页面 HUD 与 og:description 均标注 **AI 辅助创作**，并保留「程序化纹理／非真实星表」声明。

**④ 发布就绪包与验收**

`build/make_publish.py` 生成 `publish/`（22 个文件 / 约 2.8 MB / 含 `.nojekyll`），刻意保留 ESM 源、构建脚本、golden file 与三套校验脚本，使第三方能在发布目录内独立复核，而不是只拿到压缩产物。`build/verify_http.py` 在线程里起临时静态服务，逐项校验 15 个资源的 HTTP 200 / MIME / 字节哈希后自动关闭，不占用固定端口。

`python3 verify_compat.py`（作品目录）与 `python3 verify_compat.py --root publish` 各 **8/8 通过**：无 importmap/ESM、零运行时外链、og 齐全一致、预览图有效、IIFE 导出完整、WebGL 禁用端到端降级、16 组星历仍 16/16 PASS、页面与命令行自检逐行一致（最大差 0.00e+00，最大 |Δ黄经| 0.1437°）。`build/verify_http.py` 另在临时静态服务上完成 15/15 个资源的 200 / MIME / 字节哈希验收。（**v1.3 起升级为 9/9 与 16/16，并新增 23 文件，见 §4.6**；此处保留 v1.2 当时的快照。）

**⑤ 发布已执行（2026-11-07）**

| 项 | 实际结果 |
|---|---|
| 仓库 | `https://github.com/Zgch028/solar-system-3d`，`private=False`，默认分支 `main` |
| 站点 | **`https://zgch028.github.io/solar-system-3d/`**（GitHub Pages，main / 根目录，返回 HTTP 200） |
| 首次成功提交 | `75f66fb4`（22 文件 / 2 912 764 字节）；其后一次增量提交仅把 og 绝对基址统一为小写域名 |
| 线上验收 | 12 个关键资源（含中文主文件、1.3 MB IIFE 包、PNG 预览图、golden file、三套校验脚本）全部 HTTP 200、MIME 正确、**字节哈希与本地 `publish/` 逐一一致**；根路径 200 且带完整 og 元信息 |

发布链路用零依赖脚本 `build/publish_github.py`：GitHub Blob API 的 base64 通道无损上传二进制 → 一次 commit 推完 22 文件 → 开启 Pages → 轮询站点 200。发布过程中按实测报错修了三处，均属「远端 API 的真实约束」，未改动任何物理与数值：

1. 连接层偶发 `RemoteDisconnected` / `TimeoutError`：只对未收到响应的连接层异常做有限退避并**重新构造 Request**；`HTTPError` 原样返回、绝不重试，避免把 4xx/5xx 误判为抖动。
2. `auto_init=False` 的空仓库连 `POST /git/blobs` 都返回 `409 Git Repository is empty`：必须先用 **Contents API** 造出第一个提交，Git Data API 才可用；初始化文件选 `README.md`，随后被同一批文件覆盖，最终树仍是干净的 22 文件。
3. 读取引用是 `/git/ref/heads/main`（单数 `ref`），**更新引用是 `/git/refs/heads/main`（复数 `refs`）**；两路径合并成一个变量会导致 PATCH 返回 404。现已分开。另把分支名改为读取仓库实际 `default_branch`，不再硬编码 `main`。

凭据处理：使用一次性 classic PAT（`repo` scope），**仅作为进程环境变量存在**，脚本不打印、不写入文件、不写进仓库内容或工作日志；站点发布包中不含任何凭据。该令牌已完成使命，应在 GitHub → Settings → Developer settings → Tokens (classic) 立即 Delete。

**仍待人工确认**：真实手机微信内核的端到端 3D 渲染与分享卡片抓取（本地 stub 验收不能替代）；`github.io` 为境外未备案域名，微信内打开可能被提示「在浏览器中打开」。

**新增已知限制**：① 首次真机打开已实施（并暴露 §4.6 缺陷），但**修复版**尚未在真实手机微信内核做端到端渲染确认，需人工重开线上链接；② `og:image` 为绝对 URL，仓库或 owner 改名必须重跑 `set_pages_base.py` 并同步更新 README；③ `github.io` 为境外未备案域名，微信内置浏览器可能提示「在浏览器中打开」，属平台策略，非作品缺陷；④ IIFE 产物未压缩（1.3 MB），换取可逐字审计。

### §4.6 手机微信真机首次打开暴露的兼容性缺陷与修复（2026-11-07，v1.3）

**现象（用户提供真机截图，可证伪）**：手机微信内置浏览器打开线上站点，未出现 3D，而是显示内联 SVG 静态降级视图；标题写「静态降级视图 · 当前环境未启用 WebGL」，原因行写「3D 初始化异常：Can't find variable: OrbitControls」；同时「内置数值自检 16/16 PASS · 最大 |Δ黄经| 0.1437°」仍正常显示，八个行星标签与太阳齐全。

**判定**：降级兜底本身按设计生效（不白屏、物理自检不受影响），**但触发原因不正常**。原因行不是「浏览器未提供 WebGL 上下文」，说明该微信内核的 WebGL 探测是通过的、WebGL 能力可用；失败点在 3D 层代码，而非环境。

**根因**：`build/build_iife.py` 生成的 `vendor/three.iife.js` 把 415 个 Three.js 导出写成 `window.THREE = {...}`，并在文件末尾单独追加 `window.THREE.OrbitControls = OrbitControls`。3D 层前置检查 `typeof window.THREE.OrbitControls==='function'` 因此通过，但构造控制器处写的是裸标识符 `new OrbitControls(camera,canvas)`，该作用域只绑定了 `const THREE=window.THREE`。浏览器里没有全局 `OrbitControls` 变量 → `ReferenceError`（WebKit 措辞 `Can't find variable: OrbitControls`，V8 为 `OrbitControls is not defined`）→ 被 3D 层 try/catch 捕获 → 调用降级。**属符号引用错误，不是 WebGL 能力问题，也不涉及任何物理或数值。**

**为什么原来 8 项本机验收没抓到**：`verify_compat.py` 第 6 项只模拟「WebGL 被禁用」，3D 层在探测处提前 `return`，从未执行到构造控制器处；静态检查与降级路径的 DOM stub 都覆盖不到这条分支。这正是「本地 stub 不能替代真机」的实证。

**修复（3 处，全在交付层）**：

1. 构造控制器处改为 `new THREE.OrbitControls(camera,canvas)`，显式从全局命名空间取类。
2. 降级标题不再写死「当前环境未启用 WebGL」：HTML 默认中性标题并加 `id="fb-title"`，`render(reason)` 按真实原因分类 —— 含 `WebGL|上下文` → 「静态降级视图 · WebGL 不可用」；其余（初始化异常／渲染帧异常／bundle 缺失）→ 「静态降级视图 · 3D 渲染未能启动」。避免把代码缺陷误报成环境限制，也便于用户据原因行反馈。
3. 新增 `build/verify_runtime.mjs` 补上被漏掉的「WebGL 可用」路径：在 Node 里加载**真实的** `vendor/three.iife.js`（415 个真类 + OrbitControls），只把需要 GPU／DOM 事件的 `WebGLRenderer`、`OrbitControls` 换成可计数 stub，端到端执行数值层／降级层／3D 层，断言不降级、`__BOOTED`／`__MODE3D__` 已设置且两个类各构造 1 次。接入 `verify_compat.py` 成为第 9 项；第 6 项同步增加两类标题的分类断言。

**回归有效性（负向验证，实跑）**：把构造控制器处人为改回裸 `OrbitControls` 后，对临时副本执行 `node build/verify_runtime.mjs --root <副本>`，以退出码 1 失败并输出 `OrbitControls 构造次数 = 0`、`3D 层意外触发降级视图：原因：3D 初始化异常：OrbitControls is not defined`、`[3D] 初始化失败 ReferenceError: OrbitControls is not defined` —— 与截图同一异常。证明该测试确实能拦住此缺陷，而不是摆设。

**修复后验收（实跑）**：`verify_compat.py` 在作品目录与 `publish/` 各 **9/9**；`build/verify_http.py` **16/16**；`node verify.mjs` 仍 **16/16 PASS、最大 |Δ黄经| 0.1437°**，`verify_page.py` 逐行差 **0.00e+00**；规格书 V1 与技能包 `prompts-v1-web.md` 仍逐字一致（3517 字符）。`publish/` 由 22 文件增至 **23 文件 / 约 2.79 MB**（新增 `build/verify_runtime.mjs`）。物理与数值一行未动。

**修复版发布与线上复核（2026-11-07，v1.3）**：用户重新生成一枚一次性 classic PAT（`repo` scope，仅作进程环境变量、不落盘、不回显），用同一个已验证脚本 `build/publish_github.py` 做增量提交。只读比对 git tree 得到 **7 个变更**（6 个修改：中文主 HTML、`README.md`、`SOURCES.md`、`verify_compat.py`、`build/make_publish.py`、`build/verify_http.py`；1 个新增：`build/verify_runtime.mjs`），其余 16 个 blob 未动。推送后遍历 `publish/` **全部 23 个文件**逐项线上复核：HTTP 200 且**字节哈希 23/23 与本地一致**；git tree 亦为 23 blob、内容不一致 0 个、线上多出 0 个；线上主文件含 `new THREE.OrbitControls(camera,canvas)`、不含裸 `new OrbitControls(`；`og:url` / `og:image` / canonical 仍为小写 `https://zgch028.github.io/solar-system-3d/`。提交 hash 以仓库 `main` 最新一条为准（此处不写死，避免文档与远端分叉）。**§4.5 ⑤ 表格记录的是 v1.2 首发快照，不代表当前线上版本。**

**仍待人工**：修复版上线后，用同一台手机微信重新打开链接，确认 3D 正常渲染、拖拽旋转／缩放可用、分享卡片抓取正常；真机内核能力不能被任何 Node stub 替代。

---

## 5. 已知取舍声明

### 精确部分
JPL 六根数与世纪变率、开普勒方程求解、J2000 黄道坐标旋转、两个时刻的位置计算、NASA Fact Sheet 自转／轴倾／直径／周期、双尺度公式与固定随机种子、第三方参照星历的岁差换算。

### 艺术化压缩（非物理）
观赏比例的对数／幂律压缩、程序化生成的行星纹理与太阳纹理（**非真实影像**，固定种子 20261106）、土星／天王星环的宽度与卡西尼缝位置、程序化星空（**非真实星表**）、月球圆轨道半径、太阳颜色与发光强度。

### 明确省略
冥王星、小行星带、完整卫星系统（仅保留月球且为简化圆轨道）、行星摄动、相对论效应、光行时、大气散射、行星际尘埃、恒星自行。

### 与 V1 的偏差（主动声明，不静默掩盖）

| # | 要求 | 实际 | 原因 |
|---|---|---|---|
| 1 | 引用 JPL 页面自带精度表声明误差上限 | **未引用原值** | 原页不可达、PDF 不完整；改用 §4.2 的 16 组实测误差替代，不编造角秒数 |
| 2 | 与 JPL Horizons 两个时刻逐项误差表 | **判据替换**：改用 PyEphem/VSOP87 独立星历，16/16 PASS | `ssd.jpl.nasa.gov` 被代理阻断；`--online` 脚本保留、预检未通过时降级回本地。详见 §4.2 |
| 3 | 与 Stellarium / NASA Eyes 同时刻截图并排 | 未做 | 需第三方软件与人工截图，非本会话可自动完成 |
| 4 | 按 WGCCRE 极轴方向施加倾角 | 用 NASA Fact Sheet 的轴倾角值，方向按各行星 Ω 近似 | 未引入 NAIF PCK / WGCCRE 的 α₀、δ₀、W₀、W′ 完整模型 |
| 5 | 自转 W = W₀ + W′·d | W₀ 取 0，W′ = 360/|P|（deg/day） | 逆行由 >90° 轴倾表达，避免与负周期重复计入；本初子午线初始相位任意 |
| 6 | 表面纹理用 NASA/JPL 任务影像 | 程序化纹理 | 保证页面零外部资源、离线可运行；已在 HUD 与本文声明「非真实影像」 |
| 7 | UTC→TDB 完整换算 | 32.184 s + 37 闰秒近似 | 未引入 ΔT／闰秒表；对教学级 <1° 阈值影响可忽略 |
| 8 | instancing | 未使用 | 场景仅 9 个球体 + 8 条轨道线，无实例化必要 |
| 9 | 真实 NASA 纹理授权与 credit | 不适用 | 未使用任何外部影像资产 |
| 10 | `--online` 的「需联网」表述 | 改为可证伪判据：目标端点返回 200 且响应含 `$$SOE` 块，否则明确报"目标域名不可达"并降级 | 笼统的「需联网」无法被第三方判定，不合格（四问框架 Q4） |
| 11 | 页面误差表应引用同一份 golden file | 改为**内联数值快照**（16 组），与 3D 场景共用同一套函数现场重算；配 `sync_reference.py` 同步 + `verify_page.py` 复核 | 避免 `fetch('./reference.json')` 在 `file://`／部分预览服务下失败；代价是存在副本，已用同步脚本与一致性验证约束 |
| 12 | ESM CDN 固定为 `cdn.jsdelivr.net` | **最终改为本地 `vendor/`，再打成单文件 IIFE 全局包**：`vendor/three.iife.js` 由两个 ESM 原件确定性生成，页面用普通 `<script>` 引入，无 importmap / 无 ESM / 无 CDN；中途曾短暂切到 `fastly.jsdelivr.net` | 主节点 SSL 失败（HTTP 000）；本地化后页面外网 URL 数为 0，并可直接双击 `file://` 打开。属交付形态变更，不改物理与数值。详见 §4.4、§4.5 |
| 13 | 交付「单个 `index.html`」 | 主文件改名 **`太阳系八大行星动态运转.html`**（中文、易识别）；`index.html` 保留为薄重定向，不再是内容副本 | 用户反馈"打开作品名称不是中文、不易识别"；重定向保证既有链接与静态服务根路径仍可用，同时维持**单一事实来源**，避免两份内容分叉 |
| 14 | 规格 V1 §0 写「importmap 指本地 vendor，仍须静态服务」 | 改写为「普通 script + IIFE 全局包，须能 `file://` 双击打开」，并逐字同步技能包 `references/prompts-v1-web.md` | 载体从本地预览变为微信内核／GitHub Pages，属载体绑定约束（四问框架 Q1）；Q4 判据、决策链、定位卡字段均未改动，故方法论文档版本仍为 v1.1 |
| 15 | V1 未要求 WebGL 降级、分享元信息与 AI 标注 | 新增 WebGL 探测 + 内联 SVG 静态降级 + og/twitter 元信息 + `assets/preview.png` + 页面与 og 中的 AI 辅助创作标注 | 分享场景的隐含需求；均为交付形态，不动物理与数值。见 §4.5 |
| 16 | 单文件交付 | 发布版为 `publish/` 目录（v1.3 为 23 文件 / 约 2.8 MB：ESM 源、IIFE 产物、构建脚本、golden file、四套校验脚本、许可证） | 换取第三方逐字复核能力；页面运行时仍只需 1 个 HTML + 1 个 JS + 1 张分享图，且分享图对运行非必需 |
| 17 | 3D 层用裸 `OrbitControls` 标识符（IIFE 改造时残留） | 改为 `THREE.OrbitControls`；降级标题按原因分类；新增 WebGL 可用路径的运行时冒烟测试作为第 9 项验收 | 手机微信真机首次打开暴露：降级视图生效但原因是 `Can't find variable: OrbitControls`，本该显示 3D。原 8 项验收只覆盖「WebGL 禁用」分支故漏检。见 §4.6 |

### 太阳与月球的辅助数值
- 太阳直径 1 392 000 km、月球直径 3 475 km（由 Earth 12 756 km × Fact Sheet ratio 0.2724 推得）、月球恒星月 27.321661 d、地月距离取艺术化压缩值 —— **均为常用值／派生值，本会话未在线复核**，仅用于显示尺度，不参与位置计算。

---

## 6. 运行与复现

```bash
cd 02_太阳系3D作品
# 打开方式三选一（都不需要外网）：
#   ① 直接双击《太阳系八大行星动态运转.html》（file:// 可开）
#   ② python3 -m http.server 8811 → http://localhost:8811/ （自动跳中文主文件）
#   ③ 发布到静态托管（GitHub Pages）后访问站点根路径

node verify.mjs                  # 数值自检 + 本地独立星历 16 组误差表（零依赖、零网络）
node verify.mjs --online         # 可选：改与 JPL Horizons 对照；先预检，不通则明确报错并降级
node verify.mjs --json           # 机器可读输出（comparison 段含 source/pass/rows）
python3 verify_page.py           # 页面自检面板 ↔ 命令行 16 行逐位一致
python3 verify_compat.py         # 兼容加固 9 项验收（含 WebGL 禁用降级 + WebGL 可用初始化两条路径）
node build/verify_runtime.mjs    # 单独跑第 9 项：真实 THREE 下 3D 层初始化冒烟

# 兼容加固的可复现构建
python3 build/build_iife.py      # 由 vendor ESM 原件重新生成 vendor/three.iife.js
node build/verify_bundle.mjs     # 验收 416 个导出 + OrbitControls
python3 build/make_preview.py    # 由 reference.json 重画 og 分享图（构建期需 Pillow）
python3 build/make_publish.py    # 生成 publish/ 干净发布版
python3 verify_compat.py --root publish
python3 build/verify_http.py     # 临时静态服务逐项 HTTP/MIME/哈希验收后自动关闭
python3 build/set_pages_base.py <repo> [owner]   # 仓库改名时批量替换 og 绝对 URL
GITHUB_TOKEN=xxx python3 build/publish_github.py --dry-run   # 发布演练（不连网）
GITHUB_TOKEN=xxx python3 build/publish_github.py             # 一键发布到 GitHub Pages

# 重新生成第三方参照 golden file（仅此步需要 Python 与 pip）
python3 -m pip install --only-binary :all: ephem==4.2.1
python3 reference_ephem.py       # 覆写 reference.json，任何人可复核
python3 sync_reference.py        # 同步主文件内联快照（幂等）
python3 verify_page.py
```

- Three.js r160 与 OrbitControls 的 ESM 原件留在 `vendor/`，运行时只用由它们确定性生成的 `vendor/three.iife.js`（普通脚本、全局 `window.THREE`）。**页面运行不发起任何外网请求，且可直接双击 `file://` 打开**；断网也能完整显示 3D 与自检面板。`og:image` 的绝对 URL 是分享爬虫元数据，不构成运行时依赖。
- 所有参数集中在《太阳系八大行星动态运转.html》的 `CONFIG`；随机数用 `mulberry32` 固定种子 20261106；动画用 delta-time，不用帧计数。
- `reference.json` 是 golden file：校验只读它，因此**运行校验不依赖 Python、ephem 包或网络**；生成器仅供第三方重新核算。
- 页面分三段普通脚本：数值层（`window.SOLAR`）、降级层（`window.__SOLAR_FALLBACK__`，不依赖 THREE）、3D 层（IIFE + try/catch）。不加载 Three.js 也能显示 16 组误差表；WebGL 不可用时显示内联 SVG 静态视图，两者都由同一套 `stateOf()` 现场重算，可用 `verify_page.py` / `verify_compat.py` 复核。
- 元验证：让一位未读过本对话的人，按 §6 命令重跑 `verify.mjs`、`verify_page.py`、`verify_compat.py`，应得到 §4 / §4.2 完全一致的数值表与 PASS 结论，在模拟禁用 WebGL 时看到静态视图、在 WebGL 可用路径看到 3D 层完整启动；再按构建命令重跑 `build_iife.py` / `make_preview.py`，应得到同一份 IIFE 产物与同一张预览图。把主文件里的 `new THREE.OrbitControls(` 改回 `new OrbitControls(`，再跑 `build/verify_runtime.mjs` 必须以非零码失败（§4.6 负向验证）。

## 7. V1 §5 验收清单对照

| 验收项 | 状态 |
|---|---|
| 1 两个时刻位置 + 第三方星历误差表（<1°） | **PASS** —— 位置表已出；判据替换后 16/16 对照，最大 0.1437°（§4.2）；误差表已内置页面自检面板并现场重算，与命令行逐行一致（§4.3）。2026-11-07 中文命名、vendor 化、IIFE 兼容加固与 publish/ 发布版生成后多次复跑，结论不变（§4.4、§4.5） |
| 2 T²/a³ 偏差表 | PASS（最大 0.014152） |
| 3 面积速度近日点 > 远日点 | PASS |
| 4 自转周期对照、金星反向、天王星大倾角 | PASS |
| 5 Stellarium / NASA Eyes 截图并排 | 未做（需人工第三方软件） |
| 6 SOURCES.md + 已知取舍声明 | 本文件 |

**结论：全部可由本机自动核验的部分（含第三方逐项误差表）已通过，不宣称「整体达标」的部分只剩三类** —— ① JPL 原页自带精度表原值未取得（改用实测误差，不编造）；② Stellarium / NASA Eyes 截图并排需人工；③ 真实手机内核的端到端确认：微信真机已首次打开并暴露 §4.6 的兼容性缺陷（已在本机修复并补上回归测试），**修复版上线后的 3D 渲染、交互与分享卡片仍需人工复核**，小红书内核未测。此外 JPL Horizons 在线对照虽因网络阻断未执行，但已由更独立的 VSOP87 参照等价替代并公开声明，未静默掩盖。兼容加固、发布与 §4.6 修复均未改动任何物理或数值，16/16 PASS 与 0.1437° 结论保持一致。**GitHub Pages 发布已于 2026-11-07 完成，首次上线 12 个关键资源与本地发布包字节哈希逐一一致**（§4.5 ⑤）；§4.6 修复版的增量发布状态另记于工作日志。
