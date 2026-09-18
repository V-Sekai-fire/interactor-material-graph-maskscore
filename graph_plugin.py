import os

import sd
from sd.api.sdbasetypes import float2
from sd.api.sdresource import EmbedMethod
from sd.api.sdresourcesvg import SDResourceSVG
from sd.api.sdvalueint import SDValueInt
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

GRID = 160.0
HERE = os.path.dirname(os.path.abspath(__file__))
VECTOR_SOURCE = os.path.join(HERE, "vector_pattern.svg")
OUTPUT_PACKAGE = os.path.join(HERE, "out", "pattern.sbs")

PATTERN_INPUT_IMAGE = 1


def _root_quadrant(fxmap_node):
    fxmap_graph = fxmap_node.getReferencedResource()
    for node in fxmap_graph.getNodes():
        if node.getDefinition().getId() == "sbs::fxmap::paramset":
            return node
    return fxmap_graph.newNode("sbs::fxmap::paramset")


def build_vector_fxmap_graph(context, vector_source=VECTOR_SOURCE):
    """Build a compositing graph whose FX-Map scatters an imported vector pattern."""
    package = context.getSDApplication().getPackageMgr().newUserPackage()

    graph = SDSBSCompGraph.sNew(package)
    graph.setIdentifier("vector_fxmap_pattern")

    # SVG resources refuse BinaryEmbedded (SDApiError.NotSupported); the package
    # links the file instead.
    resource = SDResourceSVG.sNewFromFile(package, vector_source, EmbedMethod.Linked)
    resource.setIdentifier("vector_pattern")

    svg_node = graph.newInstanceNode(resource)
    svg_node.setPosition(float2(-2.0 * GRID, 0.0))

    fxmap_node = graph.newNode("sbs::compositing::fxmaps")
    fxmap_node.setPosition(float2(0.0, 0.0))

    output_node = graph.newNode("sbs::compositing::output")
    output_node.setPosition(float2(2.0 * GRID, 0.0))

    svg_node.newPropertyConnectionFromId(
        "unique_filter_output", fxmap_node, "inputpattern"
    )
    fxmap_node.newPropertyConnectionFromId(
        "unique_filter_output", output_node, "inputNodeOutput"
    )

    quadrant = _root_quadrant(fxmap_node)
    # Pattern "Input Image" makes the quadrant place the vector art on inputpattern
    # instead of one of the built-in morphlets.
    quadrant.setInputPropertyValueFromId(
        "patterntype", SDValueInt.sNew(PATTERN_INPUT_IMAGE)
    )
    quadrant.setInputPropertyValueFromId("imageindex", SDValueInt.sNew(0))

    return package, graph


def write_package(context=None, output_package=OUTPUT_PACKAGE):
    context = context or sd.getContext()
    package, _graph = build_vector_fxmap_graph(context)
    os.makedirs(os.path.dirname(output_package), exist_ok=True)
    context.getSDApplication().getPackageMgr().savePackageAs(package, output_package)
    return output_package


def initializeSDPlugin():
    print("material-graph-maskscore wrote %s" % write_package())


def uninitializeSDPlugin():
    pass
