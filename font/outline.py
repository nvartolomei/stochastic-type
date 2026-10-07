"""Outline plumbing: segment extraction, curved-run detection and snapping of near-axis lines."""

import math

import pathops
from fontTools.pens.basePen import BasePen


class SegPen(BasePen):
    def __init__(self):
        super().__init__(None)
        self.contours = []
        self.cur = None
        self.pt = None

    def _moveTo(self, p):
        self.cur = []
        self.start = p
        self.pt = p

    def _lineTo(self, p):
        self.cur.append(("L", self.pt, p))
        self.pt = p

    def _qCurveToOne(self, c, p):
        self.cur.append(("Q", self.pt, c, p))
        self.pt = p

    def _curveToOne(self, c1, c2, p):
        self.cur.append(("C", self.pt, c1, c2, p))
        self.pt = p

    def _closePath(self):
        if self.pt != self.start:
            self.cur.append(("L", self.pt, self.start))
        if self.cur:
            self.contours.append(self.cur)
        self.cur = None

    _endPath = _closePath


def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def cross(a, b): return a[0] * b[1] - a[1] * b[0]
def norm(a): return math.hypot(a[0], a[1])
def ang(a): return math.degrees(math.atan2(a[1], a[0])) % 360


def adiff(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def start_tangent(s):
    v = sub(s[2], s[1])
    return v if norm(v) > 1e-6 else sub(s[-1], s[1])


def end_tangent(s):
    v = sub(s[-1], s[-2])
    return v if norm(v) > 1e-6 else sub(s[-1], s[1])


def is_curved(s, tol=2.5):
    if s[0] == "L":
        return False
    a, b = s[1], s[-1]
    ch = sub(b, a)
    length = norm(ch)
    if length < 1e-6:
        return True
    n = (-ch[1] / length, ch[0] / length)
    ctrl = s[2:-1]
    return max(abs(dot(sub(c, a), n)) for c in ctrl) > tol * (2 if s[0] == "Q" else 1)


def flatten(s, k):
    out = []
    for i in range(1, k + 1):
        t = i / k
        u = 1 - t
        if s[0] == "Q":
            p0, c, p1 = s[1], s[2], s[3]
            out.append((u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0],
                        u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]))
        elif s[0] == "C":
            p0, c1, c2, p1 = s[1], s[2], s[3], s[4]
            out.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p1[0],
                        u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p1[1]))
        else:
            out.append(s[2])
    return out


def flatten_contours(path, samples=12):
    """Contours of a pathops path as polygons."""
    pen = SegPen()
    path.draw(pen)
    out = []
    for segs in pen.contours:
        pts = [segs[0][1]]
        for s in segs:
            pts += flatten(s, samples)
        out.append(pts)
    return out


def area(pts):
    return 0.5 * sum(cross(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))


def snap_lines(segs, P):
    """Make near-vertical and near-horizontal straight segments exactly so."""
    n = len(segs)
    verts = [list(s[1]) for s in segs]
    tx = [[] for _ in range(n)]
    ty = [[] for _ in range(n)]
    for i, s in enumerate(segs):
        if s[0] != "L":
            continue
        a, b = verts[i], verts[(i + 1) % n]
        d = (b[0] - a[0], b[1] - a[1])
        length = norm(d)
        if length < P["snap_min_len"]:
            continue
        phi = ang(d)
        if min(adiff(phi, 90), adiff(phi, 270)) <= P["snap_vertical"]:
            mid = (a[0] + b[0]) / 2
            tx[i].append(mid)
            tx[(i + 1) % n].append(mid)
        elif min(adiff(phi, 0), adiff(phi, 180)) <= P["snap_horizontal"]:
            mid = (a[1] + b[1]) / 2
            ty[i].append(mid)
            ty[(i + 1) % n].append(mid)
    for i in range(n):
        if tx[i]:
            verts[i][0] = sum(tx[i]) / len(tx[i])
        if ty[i]:
            verts[i][1] = sum(ty[i]) / len(ty[i])
    out = []
    for i, s in enumerate(segs):
        a, b = tuple(verts[i]), tuple(verts[(i + 1) % n])
        out.append((s[0], a) + tuple(s[2:-1]) + (b,))
    return out


def walk_contours(path, P, run_fn):
    """Rebuild `path`, passing every curved run to run_fn(pts, cyclic, segs).

    run_fn returns replacement segments or None to keep the original curve.
    A run that ends against a smooth, non-line neighbour is kept as is: the neighbour is part of the
    same curve (the base splits long curves into many small quadratics, most of them too flat to count
    as curved), and moving only some of it leaves a kink where the run stops.
    Near-axis straight lines are snapped afterwards.
    """
    pen = SegPen()
    path.draw(pen)
    contours = pen.contours
    if not contours:
        return path
    out = pathops.Path()
    wp = out.getPen()
    for segs in contours:
        n = len(segs)
        curved = [is_curved(s) for s in segs]
        corner_after = [adiff(ang(end_tangent(segs[i])), ang(start_tangent(segs[(i + 1) % n]))) > P["joint_angle"]
                        for i in range(n)]

        s0 = next((i for i in range(n) if not (curved[i] and curved[i - 1]) or corner_after[i - 1]), None)
        new = []
        if s0 is None:
            pts = [p for s in segs for p in flatten(s, P["samples"])]
            new = run_fn(pts, True, segs) or list(segs)
        else:
            i = 0
            while i < n:
                k = (s0 + i) % n
                if not curved[k]:
                    new.append(segs[k])
                    i += 1
                    continue
                j = i
                while j + 1 < n and curved[(s0 + j + 1) % n] and not corner_after[(s0 + j) % n]:
                    j += 1
                run = [segs[(s0 + q) % n] for q in range(i, j + 1)]
                first, last = (s0 + i) % n, (s0 + j) % n
                open_start = segs[first - 1][0] != "L" and not corner_after[first - 1]
                open_end = segs[(last + 1) % n][0] != "L" and not corner_after[last]
                if open_start or open_end:
                    new += run
                    i = j + 1
                    continue
                pts = [run[0][1]]
                for s in run:
                    pts += flatten(s, P["samples"])
                new += run_fn(pts, False, run) or run
                i = j + 1
        new = snap_lines(new, P)
        wp.moveTo(new[0][1])
        for s in new:
            if s[0] == "L":
                wp.lineTo(s[2])
            elif s[0] == "Q":
                wp.qCurveTo(s[2], s[3])
            else:
                wp.curveTo(s[2], s[3], s[4])
        wp.closePath()
    out.simplify(fix_winding=True)
    return out
