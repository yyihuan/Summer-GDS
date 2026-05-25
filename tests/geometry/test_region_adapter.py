from summer_gds.geometry.region_adapter import boundary_to_region, dbu_to_um, region_to_boundary, um_to_dbu
from summer_gds.model.geometry import BoundaryMetadata, BoundaryObject, GeometryContext
from summer_gds.model.protocol import LayerSpec, Point


def test_um_to_dbu_uses_half_away_from_zero():
    context = GeometryContext(unit="um", dbu=0.001)

    assert um_to_dbu(0.0005, context) == 1
    assert um_to_dbu(-0.0005, context) == -1
    assert um_to_dbu(0.0015, context) == 2
    assert um_to_dbu(-0.0015, context) == -2
    assert dbu_to_um(2, context) == 0.002


def test_boundary_to_region_round_trip_keeps_layer_and_single_boundary():
    context = GeometryContext(unit="um", dbu=0.001)
    boundary = BoundaryObject(
        points=(Point(0, 0), Point(10, 0), Point(10, 5), Point(0, 5)),
        metadata=BoundaryMetadata(owner_sid=0, source_sid=None, role="source", coordinate_unit="um"),
    )

    region_object = boundary_to_region(boundary, LayerSpec(1, 0), context, role="base_output")
    round_tripped = region_to_boundary(region_object, context, role="base_offset")

    assert region_object.layer == LayerSpec(1, 0)
    assert not region_object.region.is_empty()
    assert len(round_tripped.points) == 4
    assert {point.x for point in round_tripped.points} == {0, 10}
    assert {point.y for point in round_tripped.points} == {0, 5}
