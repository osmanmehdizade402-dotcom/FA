"""Auto-straighten slightly tilted photos (user rule: fix small tilts).

Finds near-vertical edges (walls, door frames, columns, curtains), takes the
length-weighted median of their lean and rotates the photo back by that much,
then crops the empty corners. Converging verticals from a wide lens lean in
opposite directions and cancel out in the median, so only a real camera tilt
gets corrected. Large or uncertain angles are left alone.
"""
import math

import cv2
import numpy as np
from PIL import Image

MAX_FIX = 4.0   # degrees; bigger leans are usually intentional/perspective, not tilt
MIN_FIX = 0.25  # degrees; below this nothing visible to fix


def tilt_angle(im):
    """Camera tilt in degrees (positive = photo content leans clockwise), or 0."""
    w = 1000
    small = im.convert("L").resize((w, int(im.height * w / im.width)))
    g = cv2.GaussianBlur(np.asarray(small), (3, 3), 0)
    edges = cv2.Canny(g, 60, 160)
    h = edges.shape[0]
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=60,
                            minLineLength=int(h * 0.08), maxLineGap=8)
    if lines is None:
        return 0.0
    devs, weights = [], []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        if dy < 0:
            dx, dy = -dx, -dy
        length = math.hypot(dx, dy)
        dev = math.degrees(math.atan2(dx, dy))  # 0 = perfectly vertical
        if abs(dev) <= 8:
            devs.append(dev)
            weights.append(length)
    if sum(weights) < h * 1.5:  # too little vertical structure to judge
        return 0.0
    order = np.argsort(devs)
    devs, weights = np.array(devs)[order], np.array(weights)[order]
    cum = np.cumsum(weights)
    return float(devs[np.searchsorted(cum, cum[-1] / 2)])


def straighten(im):
    a = tilt_angle(im)
    if abs(a) < MIN_FIX or abs(a) > MAX_FIX:
        return im, 0.0
    rot = im.rotate(-a, resample=Image.BICUBIC, expand=False)
    # crop the largest centred rect with the original aspect that has no empty corners
    w, h = im.size
    t = math.radians(abs(a))
    s = 1 / (math.cos(t) + math.sin(t) * max(w / h, h / w))
    cw, ch = w * s, h * s
    box = ((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2)
    return rot.crop(tuple(int(round(v)) for v in box)), a
