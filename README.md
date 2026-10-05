# interactor-material-graph-maskscore

Builds node-graph materials whose pattern is placed from vector art, then cooks and renders them without a GUI for MaskScore and EditScore.

## What it is for

The shape enters the material graph as vector art and a scatter node places it, so the pattern is resolution-independent by construction rather than a scaled raster tile. An animated vector source is converted to SVG at one frame first, and `thorvg_check.py` renders both through ThorVG and compares them, with a self-test control that must fail.

## Build and run

Convert the animated source to SVG at one frame, and check the two render alike:

```sh
python3 lottie_to_svg.py vector_pattern.lot --svg vector_pattern.svg
python3 thorvg_check.py vector_pattern.lot vector_pattern.svg
python3 thorvg_check.py vector_pattern.lot --self-test
```

Copy `graph_plugin.py` into the node-based material authoring tool's user plugin directory and restart the tool; the plugin writes the material package. Then cook and render it:

```sh
python3 cook_and_render.py
```

## Licence

There is no licence file, and the licence is not stated.
