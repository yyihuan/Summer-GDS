"""KLayout-backed GDS writer for normalized MVP geometry."""

from pathlib import Path

from mvp_summer_gds.config.errors import GDSWriteError


def write_gds(polygons, cell_name, dbu, output_file):
    if not polygons:
        raise GDSWriteError("No polygons to write; refusing to create an empty GDS.")
    output_path = Path(output_file)
    if output_path.suffix != ".gds":
        raise GDSWriteError("Output path must end with .gds: %s" % output_path)
    if output_path.parent and not output_path.parent.exists():
        raise GDSWriteError("Output directory does not exist: %s" % output_path.parent)

    try:
        import klayout.db as db
    except ImportError as exc:
        raise GDSWriteError("KLayout Python module is not installed: %s" % exc)

    layout = db.Layout()
    layout.dbu = float(dbu)
    cell = layout.create_cell(cell_name)

    try:
        for polygon in polygons:
            layer_index = layout.layer(db.LayerInfo(polygon.layer.layer, polygon.layer.datatype))
            db_points = [_to_db_point(db, point, layout.dbu) for point in polygon.points]
            cell.shapes(layer_index).insert(db.Polygon(db_points))
        layout.write(str(output_path))
    except Exception as exc:
        raise GDSWriteError("Failed to write GDS: %s" % exc)


def _to_db_point(db, point, dbu):
    return db.Point(_to_dbu(point.x, dbu), _to_dbu(point.y, dbu))


def _to_dbu(value, dbu):
    return int(round(float(value) / float(dbu)))
