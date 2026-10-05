# interactor-material-graph-maskscore

Builds node-graph materials whose pattern is placed from vector art, then cooks and renders them without a GUI for MaskScore and EditScore.

## What it is for

The shape enters the material graph as vector art and a scatter node places it, so the pattern is resolution-independent by construction rather than a scaled raster tile. An animated vector source is converted to SVG at one frame first, and `thorvg_check.py` renders both through ThorVG and compares them, with a self-test control that must fail.

## Build and run

`graph_plugin.py` runs inside the node-based material authoring tool as a user plugin and writes the material package. Then:

```sh
python3 cook_and_render.py
```

## Licence

There is no licence file, and the licence is not stated.
