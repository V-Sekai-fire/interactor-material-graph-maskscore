"""Render a Lottie frame and its converted SVG through ThorVG and compare them.

A converter that emits an SVG nothing checks is a converter that is assumed to work.
"""
import argparse
import ctypes
import os
import sys

LIBRARY = os.environ.get("THORVG_LIB", "/opt/homebrew/lib/libthorvg-1.dylib")
TVG_COLORSPACE_ARGB8888 = 1


def _thorvg(path=LIBRARY):
    library = ctypes.CDLL(path)
    library.tvg_animation_get_picture.restype = ctypes.c_void_p
    library.tvg_animation_new.restype = ctypes.c_void_p
    library.tvg_picture_new.restype = ctypes.c_void_p
    library.tvg_swcanvas_create.restype = ctypes.c_void_p
    return library


def render(source, size=256, frame=0.0, library=None):
    """One frame of a Lottie or an SVG as a size x size ARGB buffer."""
    library = library or _thorvg()
    library.tvg_engine_init(0, 0)
    canvas = library.tvg_swcanvas_create()
    buffer = (ctypes.c_uint32 * (size * size))()
    library.tvg_swcanvas_set_target(
        ctypes.c_void_p(canvas), buffer, size, size, size, TVG_COLORSPACE_ARGB8888)

    animation = None
    if source.lower().endswith((".lot", ".json")):
        animation = library.tvg_animation_new()
        picture = library.tvg_animation_get_picture(ctypes.c_void_p(animation))
    else:
        picture = library.tvg_picture_new()

    if library.tvg_picture_load(ctypes.c_void_p(picture), source.encode()) != 0:
        raise SystemExit("thorvg could not load %s" % source)
    library.tvg_picture_set_size(
        ctypes.c_void_p(picture), ctypes.c_float(size), ctypes.c_float(size))
    if animation is not None:
        library.tvg_animation_set_frame(ctypes.c_void_p(animation), ctypes.c_float(frame))

    library.tvg_canvas_add(ctypes.c_void_p(canvas), ctypes.c_void_p(picture))
    library.tvg_canvas_draw(ctypes.c_void_p(canvas), True)
    library.tvg_canvas_sync(ctypes.c_void_p(canvas))
    pixels = list(buffer)
    library.tvg_canvas_destroy(ctypes.c_void_p(canvas))
    library.tvg_engine_term(0)
    return pixels


def coverage(pixels):
    """Fraction of pixels with any alpha, the cheapest signal that something drew."""
    return sum(1 for pixel in pixels if pixel >> 24) / float(len(pixels))


def difference(left, right):
    """Mean absolute per-channel difference, 0..1."""
    total = 0
    for first, second in zip(left, right):
        for shift in (0, 8, 16, 24):
            total += abs(((first >> shift) & 0xFF) - ((second >> shift) & 0xFF))
    return total / float(len(left) * 4 * 255)


def self_test(lottie, size=128):
    """Reversing layer order must fail the comparison, or it certifies nothing."""
    import json
    import tempfile

    import lottie_to_svg

    library = _thorvg()
    document = json.loads(open(lottie).read())
    reference = render(lottie, size, 0.0, library)
    if coverage(reference) == 0:
        raise SystemExit("the Lottie frame drew nothing, so the controls prove nothing")

    good, _ = lottie_to_svg.convert(document, 0)
    wrong = dict(document, layers=list(reversed(document["layers"])))
    broken, _ = lottie_to_svg.convert(wrong, 0)

    results = []
    for name, svg in (("converted", good), ("layers reversed", broken)):
        with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as handle:
            handle.write(svg)
        delta = difference(reference, render(handle.name, size, 0.0, library))
        os.unlink(handle.name)
        results.append(delta)
        print("%-16s difference %.4f" % (name, delta))

    if results[0] > 1e-6:
        raise SystemExit("the converted SVG should match the Lottie frame exactly")
    if results[1] <= 1e-6:
        raise SystemExit("reversed layers passed, so this check certifies nothing")
    print("2 controls passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lottie")
    parser.add_argument("svg", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--frame", type=float, default=0.0)
    parser.add_argument("--tolerance", type=float, default=0.02)
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test(args.lottie)
    if not args.svg:
        parser.error("an svg is required unless --self-test is given")

    library = _thorvg()
    from_lottie = render(args.lottie, args.size, args.frame, library)
    from_svg = render(args.svg, args.size, 0.0, library)

    drawn = coverage(from_lottie)
    delta = difference(from_lottie, from_svg)
    print("lottie coverage %.4f, svg coverage %.4f, difference %.4f (tolerance %.4f)"
          % (drawn, coverage(from_svg), delta, args.tolerance))
    if drawn == 0:
        raise SystemExit("the Lottie frame drew nothing, so the comparison proves nothing")
    if delta > args.tolerance:
        raise SystemExit("converted SVG differs from the Lottie frame")
    return 0


if __name__ == "__main__":
    sys.exit(main())
