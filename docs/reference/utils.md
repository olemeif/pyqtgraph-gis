# Utils

The Utils mostly contain conversion functions from WGS84 to Web Mercator to Tile Coordinates and back.

## `latlon_to_web_mercator(lat, lon)`

Convert WGS84 coordinates to Web Mercator.

## `vectorized_wgs84_to_wm(lats, lons)`

Convert sets of WGS84 coordinates to Web Mercator.

## `web_mercator_to_latlon(x, y)`

Convert Web Mercator Coordinates to WGS84.

## `vectorized_wm_to_wgs84(x, y)`

Convert sets of Web Mercator Coordinates to WGS84.

## `web_mercator_to_tile_coords(x, y, zoom)`

Convert Web Mercator Coordinates to Tile Coordinates.

## `tile_coords_to_web_mercator_bounds(tile_x, tile_y, zoom)`

Convert Tile Coordinates to Web Mercator bounds of the Tile.