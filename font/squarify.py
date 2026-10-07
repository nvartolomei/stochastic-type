"""Pushes curved runs toward superellipses.

Every sample on a curve is displaced along its outward normal by an amount
proportional to the local radius, weighted so that nothing moves where the
tangent is axis-aligned and the push peaks at 45 degrees. Outlines keep their
topology, so there is nothing to fail on junction-heavy glyphs.
"""

import math

from outline import add, cross, dot, mul, norm, sub, walk_contours

DEFAULTS = dict(
    squircle_n=3.2,     # 2 is a circle, higher is squarer
    radius_cap=260,
    taper=90,
    smooth_passes=3,
    samples=14,
    split=2,
    joint_angle=28,
    snap_vertical=7,
    snap_horizontal=5,
    snap_min_len=60,
)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def unit(v):
    n = norm(v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (1.0, 0.0)


def intersect_rays(p0, t0, p1, t1):
    det = cross(t0, t1)
    if abs(det) < 1e-4:
        return None
    d = sub(p1, p0)
    a = cross(d, t1) / det
    b = cross(d, t0) / det
    return a, b


def displace_points(pts, cyclic, P):
    """Returns (displaced points, arclength positions, total length)."""
    n = len(pts)
    if n < 6:
        return None, None, None
    k_push = 2 ** (0.5 - 1 / P["squircle_n"]) - 1

    def at(i):
        return pts[i % n] if cyclic else pts[max(0, min(n - 1, i))]

    s = [0.0]
    for i in range(1, n):
        s.append(s[-1] + norm(sub(pts[i], pts[i - 1])))
    total = s[-1] + (norm(sub(pts[0], pts[-1])) if cyclic else 0)

    tang = [unit(sub(at(i + 2), at(i - 2))) for i in range(n)]
    kappa = []
    for i in range(n):
        a, b = tang[(i - 2) % n if cyclic else max(0, i - 2)], tang[(i + 2) % n if cyclic else min(n - 1, i + 2)]
        da = math.atan2(cross(a, b), dot(a, b))
        ds = norm(sub(at(i + 2), at(i - 2))) or 1.0
        kappa.append(da / ds)
    kappa = [(kappa[(i - 1) % n] + 2 * kappa[i] + kappa[(i + 1) % n]) / 4 for i in range(n)] if cyclic else \
            [(kappa[max(0, i - 1)] + 2 * kappa[i] + kappa[min(n - 1, i + 1)]) / 4 for i in range(n)]

    signed = []
    for i in range(n):
        k = kappa[i]
        t = tang[i]
        left = (-t[1], t[0])
        outward = (-left[0], -left[1]) if k > 0 else left
        psi = math.atan2(outward[1], outward[0])
        weight = math.sin(2 * psi) ** 2
        cap = P["radius_cap"]
        radius = min(1 / max(abs(k), 1e-9), cap) * smoothstep(0.1, 0.7, abs(k) * cap)
        signed.append((1 if k <= 0 else -1) * k_push * radius * weight)

    kernel = [1, 2, 3, 2, 1]
    for _ in range(P["smooth_passes"]):
        signed = [sum(w * signed[(i + o - 2) % n if cyclic else max(0, min(n - 1, i + o - 2))]
                      for o, w in enumerate(kernel)) / 9 for i in range(n)]

    disp = []
    for i in range(n):
        t = tang[i]
        left = (-t[1], t[0])
        taper = 1.0 if cyclic else smoothstep(0, P["taper"], min(s[i], total - s[i]))
        d = signed[i] * taper
        disp.append((pts[i][0] + left[0] * d, pts[i][1] + left[1] * d))

    return disp, s, total


def soften_run(pts, cyclic, P, segs):
    n = len(pts)
    disp, _, _ = displace_points(pts, cyclic, P)
    if disp is None:
        return None
    K = P["samples"]
    nseg = len(segs)
    breaks = []
    for si in range(nseg):
        end = (K * (si + 1) - 1) if cyclic else K * (si + 1)
        mid = end - K // 2
        if P["split"] >= 2:
            breaks.append(mid % n if cyclic else mid)
        breaks.append(end % n if cyclic else end)
    if not cyclic:
        breaks = [0] + breaks
    else:
        breaks = sorted(set(breaks))

    def dtang(i):
        if cyclic:
            return unit(sub(disp[(i + 1) % n], disp[(i - 1) % n]))
        return unit(sub(disp[min(n - 1, i + 1)], disp[max(0, i - 1)]))

    out = []
    pairs = zip(breaks, breaks[1:] + ([breaks[0]] if cyclic else []))
    for b0, b1 in pairs:
        p0, p1 = disp[b0], disp[b1]
        chord = norm(sub(p1, p0))
        if chord < 1e-6:
            continue
        r = intersect_rays(p0, dtang(b0), p1, dtang(b1))
        if r and r[0] > 0 and r[1] < 0 and r[0] < 1.4 * chord and -r[1] < 1.4 * chord:
            c = add(p0, mul(dtang(b0), r[0]))
        else:
            idx = list(range(b0 + 1, b1 if b1 > b0 else b1 + n))
            if not idx:
                out.append(("L", p0, p1))
                continue
            num = (0.0, 0.0)
            den = 0.0
            for i in idx:
                t = (i - b0) / ((b1 - b0) % n or n)
                a_, b_, e_ = (1 - t) ** 2, 2 * t * (1 - t), t * t
                q = disp[i % n]
                target = sub(sub(q, mul(p0, a_)), mul(p1, e_))
                num = add(num, mul(target, b_))
                den += b_ * b_
            c = mul(num, 1 / den) if den else mul(add(p0, p1), 0.5)
        out.append(("Q", p0, c, p1))
    return out


def soften(path, params=None):
    P = dict(DEFAULTS)
    if params:
        P.update(params)
    return walk_contours(path, P, lambda pts, cyclic, segs: soften_run(pts, cyclic, P, segs))
