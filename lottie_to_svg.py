"""One frame of a Lottie animation as SVG, so a vector source stays vector.

The spec is at https://lottie.github.io/lottie-spec/latest/; conformance of a file
this workspace emits is gated by `scripts/check_lottie_spec.py` in the manuals repo.
"""
import argparse
import json
import os
import sys

SHAPE_LAYER = 4


def sample(prop, frame):
    """Value of a Lottie property at a frame: static, held, or linearly interpolated."""
    if not isinstance(prop, dict) or "k" not in prop:
        return prop
    if not prop.get("a"):
        return prop["k"]
    keys = prop["k"]
    first = keys[0]
    if frame <= first.get("t", 0):
        return first.get("s", first.get("k"))
    for current, following in zip(keys, keys[1:]):
        start, end = current.get("t", 0), following.get("t", 0)
        if not start <= frame < end:
            continue
        begin = current.get("s", current.get("k"))
        if current.get("h") or end == start:
            return begin
        finish = current.get("e", following.get("s", begin))
        ratio = (frame - start) / float(end - start)
        if isinstance(begin, list):
            return [b + (f - b) * ratio for b, f in zip(begin, finish)]
        return begin + (finish - begin) * ratio
    last = keys[-1]
    return last.get("s", last.get("k"))


def path_data(shape):
    """A Lottie bezier (v vertices, i/o tangents, c closed) as SVG path data."""
    vertices = shape.get("v") or []
    if not vertices:
        return ""
    tangents_in = shape.get("i") or [[0, 0]] * len(vertices)
    tangents_out = shape.get("o") or [[0, 0]] * len(vertices)
    parts = ["M %g %g" % (vertices[0][0], vertices[0][1])]
    span = len(vertices) if shape.get("c") else len(vertices) - 1
    for index in range(span):
        following = (index + 1) % len(vertices)
        start, end = vertices[index], vertices[following]
        out, into = tangents_out[index], tangents_in[following]
        parts.append("C %g %g %g %g %g %g" % (
            start[0] + out[0], start[1] + out[1],
            end[0] + into[0], end[1] + into[1],
            end[0], end[1],
        ))
    if shape.get("c"):
        parts.append("Z")
    return " ".join(parts)


def _colour(value, opacity):
    red, green, blue = (int(round(channel * 255)) for channel in value[:3])
    alpha = (opacity if opacity is not None else 100) / 100.0
    return "rgb(%d,%d,%d)" % (red, green, blue), alpha


def _transform(node, frame):
    anchor = sample(node.get("a", {"a": 0, "k": [0, 0]}), frame)
    position = sample(node.get("p", {"a": 0, "k": [0, 0]}), frame)
    scale = sample(node.get("s", {"a": 0, "k": [100, 100]}), frame)
    rotation = sample(node.get("r", {"a": 0, "k": 0}), frame)
    pieces = ["translate(%g %g)" % (position[0], position[1])]
    if rotation:
        pieces.append("rotate(%g)" % rotation)
    if scale[0] != 100 or scale[1] != 100:
        pieces.append("scale(%g %g)" % (scale[0] / 100.0, scale[1] / 100.0))
    if anchor[0] or anchor[1]:
        pieces.append("translate(%g %g)" % (-anchor[0], -anchor[1]))
    return " ".join(pieces)


def _geometry(item, frame):
    kind = item.get("ty")
    if kind == "sh":
        data = path_data(sample(item["ks"], frame))
        return '<path d="%s"/>' % data if data else ""
    if kind == "el":
        centre = sample(item["p"], frame)
        size = sample(item["s"], frame)
        return '<ellipse cx="%g" cy="%g" rx="%g" ry="%g"/>' % (
            centre[0], centre[1], size[0] / 2.0, size[1] / 2.0)
    if kind == "rc":
        centre = sample(item["p"], frame)
        size = sample(item["s"], frame)
        radius = sample(item.get("r", {"a": 0, "k": 0}), frame)
        return '<rect x="%g" y="%g" width="%g" height="%g" rx="%g"/>' % (
            centre[0] - size[0] / 2.0, centre[1] - size[1] / 2.0,
            size[0], size[1], radius)
    return ""


def _paint(items, frame):
    style = {"fill": "none", "stroke": "none"}
    for item in items:
        if item.get("ty") == "fl":
            colour, alpha = _colour(sample(item["c"], frame), sample(item.get("o"), frame))
            style["fill"] = colour
            style["fill-opacity"] = "%g" % alpha
        elif item.get("ty") == "st":
            colour, alpha = _colour(sample(item["c"], frame), sample(item.get("o"), frame))
            style["stroke"] = colour
            style["stroke-opacity"] = "%g" % alpha
            style["stroke-width"] = "%g" % sample(item["w"], frame)
            style["stroke-linecap"] = {1: "butt", 2: "round", 3: "square"}.get(item.get("lc"), "butt")
            style["stroke-linejoin"] = {1: "miter", 2: "round", 3: "bevel"}.get(item.get("lj"), "miter")
    return " ".join('%s="%s"' % pair for pair in sorted(style.items()))


def _group(node, frame):
    items = node.get("it", [])
    geometry = [_geometry(item, frame) for item in items]
    geometry = [shape for shape in geometry if shape]
    nested = [_group(item, frame) for item in items if item.get("ty") == "gr"]
    nested = [shape for shape in nested if shape]
    if not geometry and not nested:
        return ""
    transform = next((item for item in items if item.get("ty") == "tr"), None)
    opening = '<g %s' % _paint(items, frame)
    if transform:
        opening += ' transform="%s"' % _transform(transform, frame)
    return opening + ">" + "".join(geometry + nested) + "</g>"


def convert(document, frame=0):
    """One frame of a Lottie document as an SVG string."""
    width, height = document.get("w", 512), document.get("h", 512)
    body = []
    unsupported = []
    # Lottie paints the first layer on top; SVG paints the last one on top.
    for layer in reversed(document.get("layers", [])):
        if layer.get("ty") != SHAPE_LAYER:
            unsupported.append(layer.get("nm") or layer.get("ty"))
            continue
        transform = _transform(layer.get("ks", {}), frame)
        drawn = "".join(_group(node, frame) for node in layer.get("shapes", []))
        if drawn:
            body.append('<g transform="%s">%s</g>' % (transform, drawn))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
        '%s</svg>' % (width, height, width, height, "".join(body))
    ), unsupported


def convert_file(lottie_path, svg_path=None, frame=0):
    with open(lottie_path) as handle:
        document = json.load(handle)
    svg, unsupported = convert(document, frame)
    svg_path = svg_path or os.path.splitext(lottie_path)[0] + ".svg"
    with open(svg_path, "w") as handle:
        handle.write(svg)
    return svg_path, unsupported


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lottie")
    parser.add_argument("--svg")
    parser.add_argument("--frame", type=float, default=0)
    args = parser.parse_args(argv)
    written, unsupported = convert_file(args.lottie, args.svg, args.frame)
    if unsupported:
        # Named and counted: a skipped layer must not read as a clean conversion.
        print("skipped %d non-shape layers: %s" % (len(unsupported), ", ".join(map(str, unsupported))),
              file=sys.stderr)
    print(written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
