import argparse
import os
import shutil
import subprocess
import sys

TOOL_DIR = os.path.join(
    os.path.expanduser("~"),
    "Library/Application Support/Steam/steamapps/common",
    "Substance 3D Designer 2022/Adobe Substance 3D Designer.app/Contents/MacOS",
)


def _tool(name):
    found = shutil.which(name) or os.path.join(TOOL_DIR, name)
    if not os.path.exists(found):
        raise SystemExit("missing %s; set PATH or install the authoring tool" % name)
    return found


def cook(package, out_dir):
    """Compile a .sbs package into the .sbsar the renderer consumes."""
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        [_tool("sbscooker"), "--inputs", package, "--output-path", out_dir],
        check=True,
    )
    return os.path.join(out_dir, os.path.splitext(os.path.basename(package))[0] + ".sbsar")


def render(archive, out_dir, size=9):
    os.makedirs(out_dir, exist_ok=True)
    subprocess.run(
        [
            _tool("sbsrender"),
            "render",
            "--inputs", archive,
            "--output-path", out_dir,
            "--output-format", "png",
            "--set-value", "$outputsize@%d,%d" % (size, size),
        ],
        check=True,
    )
    return sorted(
        os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".png")
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", default=os.path.join("out", "pattern.sbs"))
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--size", type=int, default=9)
    args = parser.parse_args(argv)

    archive = cook(args.package, args.out_dir)
    renders = render(archive, args.out_dir, args.size)
    if not renders:
        raise SystemExit("cooked %s but rendered no image" % archive)
    print("\n".join(renders))
    return 0


if __name__ == "__main__":
    sys.exit(main())
