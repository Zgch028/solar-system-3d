#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reference_ephem.py —— 生成第三方独立星历参照数据 reference.json

用途
  为 verify.mjs 提供「外部判卷」的 golden file：本模型按 JPL SSD 根数外推，
  参照值由 PyEphem / libastro 的 VSOP87 解析理论独立算出。两者数据源、
  算法与代码均不同，因此比对不是自证。

为什么用它替代 JPL Horizons 在线对照
  Horizons 的唯一数据端点 https://ssd.jpl.nasa.gov/api/horizons.api
  在部分网络环境（含本作品构建环境）被代理阻断，返回 HTTP 000 / 502。
  VSOP87 是独立于 JPL DE 数值积分的解析行星理论，无需下载星历文件、
  无运行时网络依赖，且对本作品两个检验时刻的精度远优于教学级 1° 阈值。
  这是判据替换，必须写入 SOURCES.md，不得静默掩盖。

依赖与复现
  python3 -m pip install --only-binary :all: ephem==4.2.1
  python3 reference_ephem.py            # 生成同目录 reference.json

坐标系口径（关键，勿省略）
  PyEphem 的 body.hlong / body.hlat 是「当日黄道与当日春分点」下的日心黄经、
  黄纬；本模型输出的是 J2000 黄道系。两者相差黄经总岁差 p：
      p(角秒) = 5028.796195*T + 1.1054348*T^2
                + 0.00007964*T^3 - 0.000023857*T^4
  其中 T = (JD_TDB - 2451545.0) / 36525（儒略世纪，自 J2000 起）。
  换算：lon_J2000 = (lon_date - p_deg) mod 360
  这是黄经岁差的一阶近似，忽略黄道面自身旋转与章动，残差估计 < 0.01°，
  远小于 1° 阈值；实测见 SOURCES.md 的误差表。

  八颗行星取同一路径：七颗用各自 body.hlong；PyEphem 无 Earth 类，
  地球改用 ephem.Sun().hlong（即地球的日心黄经，已实测与
  Ecliptic(Sun, epoch=date).lon - 180 一致），日距用 Sun.earth_distance。

时间口径
  本模型 jdTDB(UTC) = jdUTC + (32.184 + 37) 秒，即 TDB = UTC + 69.184 s。
  因此「2000-01-01 12:00 TDB」对应 UTC 11:58:56.816 (= J2000.0)，
  「2026-01-01 00:00 UTC」在 PyEphem 中直接按该 UTC 时刻计算，
  两者表示的是同一物理瞬间，无需再做时标平移。
  闰秒取常数 37，未引入 ΔT 表，见 SOURCES.md 已知取舍。
"""

import json
import math
import os
from datetime import datetime, timezone

import ephem

R2D = 180.0 / math.pi
J2000_JD = 2451545.0
TT_MINUS_TAI_S = 32.184
LEAP_SECONDS = 37

# (中文名, PyEphem 类, 说明)
BODIES = [
    ("水星", ephem.Mercury, "Mercury.hlong / sun_distance"),
    ("金星", ephem.Venus, "Venus.hlong / sun_distance"),
    ("地球", ephem.Sun, "Sun.hlong / earth_distance（无 Earth 类）"),
    ("火星", ephem.Mars, "Mars.hlong / sun_distance"),
    ("木星", ephem.Jupiter, "Jupiter.hlong / sun_distance"),
    ("土星", ephem.Saturn, "Saturn.hlong / sun_distance"),
    ("天王星", ephem.Uranus, "Uranus.hlong / sun_distance"),
    ("海王星", ephem.Neptune, "Neptune.hlong / sun_distance"),
]

# 与 verify.mjs 的 EPOCHS 一一对应；utc 为 PyEphem 输入时刻
EPOCHS = [
    {
        "label": "2000-01-01 12:00 TDB",
        "utc": "2000/01/01 11:58:56.816",
        "jdTDB": J2000_JD,
    },
    {
        "label": "2026-01-01 00:00 UTC",
        "utc": "2026/01/01 00:00:00",
        # jdUTC(2026-01-01T00:00:00Z) = 2461041.5
        "jdTDB": 2461041.5 + (TT_MINUS_TAI_S + LEAP_SECONDS) / 86400.0,
    },
]


def precession_deg(jd_tdb):
    """黄经总岁差 p（度），Meeus 《Astronomical Algorithms》多项式。"""
    t = (jd_tdb - J2000_JD) / 36525.0
    p_arcsec = (
        5028.796195 * t
        + 1.1054348 * t ** 2
        + 0.00007964 * t ** 3
        - 0.000023857 * t ** 4
    )
    return t, p_arcsec / 3600.0


def build():
    epochs = []
    for ep in EPOCHS:
        t, p_deg = precession_deg(ep["jdTDB"])
        planets = []
        for cn, cls, note in BODIES:
            body = cls()
            body.compute(ep["utc"])
            lon_date = float(body.hlong) * R2D % 360.0
            lat_date = float(body.hlat) * R2D
            r_au = body.earth_distance if cls is ephem.Sun else body.sun_distance
            planets.append({
                "name": cn,
                "lonDate": round(lon_date, 8),
                "latDate": round(lat_date, 8),
                "lonJ2000": round((lon_date - p_deg) % 360.0, 8),
                "rAU": round(float(r_au), 9),
                "accessor": note,
            })
        epochs.append({
            "label": ep["label"],
            "utc": ep["utc"],
            "jdTDB": round(ep["jdTDB"], 9),
            "T": round(t, 9),
            "precessionDeg": round(p_deg, 9),
            "planets": planets,
        })

    return {
        "meta": {
            "generator": "reference_ephem.py",
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": "PyEphem/VSOP87",
            "ephemVersion": ephem.__version__,
            "theory": "PyEphem 4.2.1 (libastro / XEphem)，行星解析理论 VSOP87 截断实现；独立于 JPL DE 数值积分星历",
            "install": "python3 -m pip install --only-binary :all: ephem==4.2.1",
            "frame": "原始 hlong 为当日黄道/当日春分点；lonJ2000 = (lonDate - precessionDeg) mod 360",
            "precession": "p_arcsec = 5028.796195*T + 1.1054348*T^2 + 0.00007964*T^3 - 0.000023857*T^4；T=(JD_TDB-2451545.0)/36525",
            "timeScale": "TDB = UTC + 69.184 s（32.184 s + 37 闰秒常数近似）；两个时刻与本模型同一物理瞬间",
            "knownLimits": "黄经岁差一阶近似，忽略黄道面旋转、章动与光行差；估计残差 < 0.01°",
            "toleranceDeg": 1.0,
            "note": "本文件是 golden file：verify.mjs 只读它，不依赖 Python 或网络；重跑本脚本可重新生成。",
        },
        "epochs": epochs,
    }


if __name__ == "__main__":
    data = build()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("已生成", out)
    for ep in data["epochs"]:
        print(" ", ep["label"], " T=%.6f  p=%.6f°" % (ep["T"], ep["precessionDeg"]))
