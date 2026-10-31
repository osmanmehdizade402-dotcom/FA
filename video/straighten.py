"""Auto-straighten photos (user rule: walls, doors, columns must stand straight).

Phone wide-angle shots have two problems: the camera is rolled a little (everything
leans the same way) and pitched up/down (verticals converge towards a point above or
below the picture, "keystone"). Both are fixed with one perspective warp:

1. Find long near-vertical edges (walls, door frames, curtains, columns, cypresses).
2. Estimate their common vanishing point V with RANSAC + least squares.
3. Pick the largest quad inside the photo whose left/right sides are lines through V
   and warp it to a rectangle, so every line through V becomes vertical.

Corrections are partial (STRENGTH) so very wide shots still look natural, and photos
with too little vertical structure are left alone.
"""
import math

import cv2
import numpy as np
from PIL import Image

STRENGTH = 0.9      # 1.0 = perfectly parallel verticals
MAX_LEAN = 12.0     # degrees; steeper segments (floor stripes, railings) are not verticals
MIN_SHIFT = 0.004   # fraction of width; smaller corrections are skipped
MAX_SHIFT = 0.16    # fraction of width per corner; bigger means a bad estimate


def _segments(im, w=1000):
    s = w / im.width
    small = im.convert("L").resize((w, int(im.height * s)))
    g = cv2.GaussianBlur(np.asarray(small), (3, 3), 0)
    edges = cv2.Canny(g, 50, 150)
    h = edges.shape[0]
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=50,
                            minLineLength=int(h * 0.07), maxLineGap=6)
    segs = []
    if lines is None:
        return segs, s
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        if abs(math.degrees(math.atan2(dx, abs(dy) + 1e-9))) <= MAX_LEAN:
            segs.append((x1 / s, y1 / s, x2 / s, y2 / s, math.hypot(dx, dy) / s))
    return segs, s


def _line(seg):
    x1, y1, x2, y2, _ = seg
    l = np.cross([x1, y1, 1.0], [x2, y2, 1.0])
    return l / np.hypot(l[0], l[1])


def vanishing_point(im):
    """Homogeneous vertical vanishing point, or None if the photo has too few verticals."""
    segs, _ = _segments(im)
    if len(segs) < 6 or sum(s[4] for s in segs) < im.height * 1.5:
        return None
    L = np.array([_line(s) for s in segs])
    wts = np.array([s[4] for s in segs])
    rng = np.random.default_rng(0)
    best, best_score = None, -1
    diag = math.hypot(im.width, im.height)
    for _ in range(400):
        i, j = rng.choice(len(L), 2, replace=False, p=wts / wts.sum())
        v = np.cross(L[i], L[j])
        if np.linalg.norm(v) < 1e-12:
            continue
        v = v / np.linalg.norm(v)
        if not _vertical_vp(v, im.height):
            continue
        score = _inlier_weight(L, wts, v, segs, diag)
        if score > best_score:
            best, best_score = v, score
    if best is None:
        return None
    inl = _inliers(L, best, segs, diag)
    if wts[inl].sum() < 0.35 * wts.sum() or inl.sum() < 5:
        return None
    A = L[inl] * wts[inl, None]
    v = np.linalg.svd(A)[2][-1]  # least-squares point closest to all inlier lines
    v = v / np.linalg.norm(v)
    return v if _vertical_vp(v, im.height) else None


def _vertical_vp(v, H):
    """A vertical vanishing point lies far above or below the frame (or at infinity)."""
    if abs(v[2]) < 1e-12:
        return abs(v[1]) > abs(v[0])
    y = v[1] / v[2]
    return y < -0.6 * H or y > 1.6 * H


def _inliers(L, wts_or_v, segs, diag):
    v = wts_or_v
    ang = []
    for seg in segs:
        x1, y1, x2, y2, _ = seg
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # direction from segment midpoint towards V (handles V at infinity)
        dx, dy = v[0] - mx * v[2], v[1] - my * v[2]
        a1 = math.atan2(x2 - x1, y2 - y1)
        a2 = math.atan2(dx, dy)
        d = abs((a1 - a2 + math.pi / 2) % math.pi - math.pi / 2)
        ang.append(d)
    return np.array(ang) < math.radians(1.2)


def _inlier_weight(L, wts, v, segs, diag):
    return wts[_inliers(L, v, segs, diag)].sum()


def _x_at(line, y):
    a, b, c = line
    return -(b * y + c) / a


def _lean(im):
    """Length-weighted mean |lean| (deg) of near-vertical segments."""
    segs, _ = _segments(im)
    if not segs:
        return 0.0
    l = [abs(math.degrees(math.atan2(s[2] - s[0], abs(s[3] - s[1]) + 1e-9))) for s in segs]
    return float(np.average(l, weights=[s[4] for s in segs]))


def straighten(im):
    """Perspective-correct, but keep the original if the result is not clearly straighter."""
    out, shift = _straighten(im)
    if shift and _lean(out) > _lean(im) - 0.1:
        return im, 0.0
    return out, shift


def _straighten(im):
    """Returns (corrected image, max corner shift in degrees-equivalent for logging)."""
    v = vanishing_point(im)
    if v is None:
        return im, 0.0
    W, H = im.size
    if abs(v[2]) > 1e-12 and 0 <= v[1] / v[2] <= H:
        return im, 0.0  # V inside the frame: not a vertical vanishing point
    corners = {}
    for side, xs in (("l", 0.0), ("r", float(W))):
        a = np.cross(v, [xs, 0.0, 1.0])   # line through V and top corner
        b = np.cross(v, [xs, H, 1.0])     # line through V and bottom corner
        xa, xb = _x_at(a, H), _x_at(b, 0.0)
        inner_a = xa >= xs if side == "l" else xa <= xs
        if inner_a:
            corners[side] = ((xs, 0.0), (xa, float(H)))
        else:
            corners[side] = ((xb, 0.0), (xs, float(H)))
    (tlx, _), (blx, _) = corners["l"]
    (trx, _), (brx, _) = corners["r"]
    src = np.float32([[tlx, 0], [trx, 0], [brx, H], [blx, H]])
    full = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    src = full + (src - full) * STRENGTH
    shift = np.abs(src - full).max() / W
    if shift < MIN_SHIFT or shift > MAX_SHIFT:
        return im, 0.0
    top_w = src[1][0] - src[0][0]
    bot_w = src[2][0] - src[3][0]
    out_w = int(round((top_w + bot_w) / 2))
    dst = np.float32([[0, 0], [out_w, 0], [out_w, H], [0, H]])
    M = cv2.getPerspectiveTransform(src, dst)
    arr = cv2.warpPerspective(np.asarray(im), M, (out_w, H), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(arr), shift * 100


def tilt_angle(im):
    """Kept for callers/logs: mean lean (deg) of the verticals before correction."""
    segs, _ = _segments(im)
    if not segs:
        return 0.0
    leans = [math.degrees(math.atan2(s[2] - s[0], s[3] - s[1] if s[3] != s[1] else 1e-9)) for s in segs]
    leans = [(l + 90) % 180 - 90 for l in leans]
    return float(np.average(leans, weights=[s[4] for s in segs]))
