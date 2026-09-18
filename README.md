# Material Graph MaskScore

Builds node-graph materials whose pattern comes from an FX-Map driven by vector art, then cooks and renders them headlessly for MaskScore.

## Purpose
Generate MaskScore/EditScore material datasets from a node-based material authoring
tool, so a pattern is resolution-independent by construction: the shape enters the
graph as vector art and the FX-Map places it, rather than a raster tile being scaled.

## Graph shape
1. A vector-graphics resource is imported into the package and dropped in as an SVG node.
2. That node feeds the FX-Map node's first input image.
3. The FX-Map's root Quadrant renders with pattern `Input Image`, index 0, so the
   placed pattern is the vector art rather than one of the built-in morphlets.
4. The Quadrant's four outputs recurse, scattering the same vector pattern.
5. An output node exposes the result as a grayscale channel.

## Workflow
1. `graph_plugin.py` runs inside the authoring tool and writes `out/pattern.sbs`.
2. `cook_and_render.py` cooks that package and renders it with no GUI.
3. Score the renders with EditScore/MaskScore.

## Install
Copy `graph_plugin.py` into the user plugin directory
(`~/Documents/Adobe/Adobe Substance 3D Designer/python/sduserplugins/`) and restart
the application; it runs on load and reports the package it wrote.
