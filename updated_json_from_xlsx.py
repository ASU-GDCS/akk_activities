#!/usr/bin/env python
import pandas
import sys, os
import shapely.geometry as sgeom
import geopandas

sheet_name = "With Coral Counts"

if len(sys.argv) < 1:
    raise RuntimeError("No excel file specified")

xlsx = sys.argv[1]
# xlsx="Akoakoa_Restoration_Activities_20250311.xlsx"


def string_date(dat):
    if isinstance(dat, int):
        return str(dat)
    else:
        return f"{dat.month}/{dat.day}/{dat.year}"


datestr = (
    os.path.basename(xlsx)
    .replace("Akoakoa_Restoration_Activities_", "")
    .replace(".xlsx", "")
)

ofile = os.path.join(os.path.dirname(xlsx), f"AkoakoaWHIRestoration_{datestr}.geojson")

if not os.path.exists(ofile):
    tab = pandas.ExcelFile(xlsx).parse(sheet_name)

    tab.Date = [string_date(d) for d in tab.Date]

    geoms = [sgeom.Point(r.Longitude, r.Latitude) for _, r in tab.iterrows()]

    ##We have to drop Count field ArcGIS will complain if we change the fields
    gdf = geopandas.GeoDataFrame(
        tab[["Date", "Location", "Activity", "SpeciesInfo", "Notes"]],
        crs="EPSG:4326",
        geometry=geoms,
    )

    gdf.to_file(ofile, driver="GeoJSON", index=False)

print(ofile)
