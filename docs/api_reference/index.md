# API Reference

## MapWidget

```python
class pyqtgraph-gis.MapWidget(
    tile_server_url: str,
    headers: str | None = None,
    parent: QtCore.QObject | None = None,
    attribution_text: str | None = None,
    **kwargs
)
```

Extends from [pyqtgraph.PlotWidget](https://pyqtgraph.readthedocs.io/en/latest/api_reference/widgets/plotwidget.html).

PlotWidget that loads map tiles from a given Tile Provider into the background of the plot area.

### Parameters

- `tile_server_url` (str): URL of the Tile Provider API.
- `headers` (str or None, default None): Headers for the API Request.
- `parent` ([QtCore.QObject](https://doc.qt.io/qt-6/qobject.html) or None, default None): Parent QObject for the Widget.
- `attribution_text` (str or None, default None): Attribution Text shown in the bottom right corner of the map area, for attributions to the tile or data providers.

### Signals

- `sigMapClicked` ([Signal](https://doc.qt.io/qt-6/signalsandslots.html)): Signal that is emitted when the map is clicked. Emits the latitude and longitude of the clicked point.
- `sigMouseMoved` ([Signal](https://doc.qt.io/qt-6/signalsandslots.html)): Signal that is emitted when the mouse is moved over the map. Emits the latitude and lomgitude of the mouse position.

### `plot_lines(lats: list, lons: list, *args, **kwargs)`

Plots sets of WGS84 latitudes and longitudes to the map as a line. Returns a [pyqtgraph.PlotItem](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/plotitem.html) object.

#### Parameters

- `lats` (list): List of latitudes to plot.
- `lons` (list): List of longitudes to plot.

### `add_scatter(lats: list, lons: list, **kwargs)`

Plots sets of WGS84 latitudes and longitudes to the map as points. Returns a [pyqtgraph.ScatterPlotItem](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/scatterplotitem.html) object.

#### Parameters

- `lats` (list): List of latitudes to plot.
- `lons` (list): List of longitudes to plot.

### `add_2d_array(image_data: numpy.ndarray, min_lat: float, min_lon: float, max_lat: float, max_lon: float, **kwargs)`

Plot an image to the map. Takes the image data as a [numpy.ndarray](https://numpy.org/devdocs/reference/generated/numpy.ndarray.html) and bounding box coordinates and returns a [pyqtgraph.ImageItem](https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/imageitem.html) object.

#### Parameters

- `image_data` ([numpy.ndarray](https://numpy.org/devdocs/reference/generated/numpy.ndarray.html)): Image as a numpy.ndarray.
- `min_lat` (float): Bounding Box lower WGS84 latitude.
- `min_lon` (float): Bounding Box lower WGS84 longitude.
- `max_lat` (float): Bounding Box higher WGS84 latitude.
- `max_lon` (float): Bounding Box higher WGS84 longitude.

## Utils

The Utils mostly contain conversion functions from WGS84 to Web Mercator to Tile Coordinates and back.

### `latlon_to_web_mercator(lat, lon)`

Convert WGS84 coordinates to Web Mercator.

### `vectorized_wgs84_to_wm(lats, lons)`

Convert sets of WGS84 coordinates to Web Mercator.

### `web_mercator_to_latlon(x, y)`

Convert Web Mercator Coordinates to WGS84.

### `vectorized_wm_to_wgs84(x, y)`

Convert sets of Web Mercator Coordinates to WGS84.

### `web_mercator_to_tile_coords(x, y, zoom)`

Convert Web Mercator Coordinates to Tile Coordinates.

### `tile_coords_to_web_mercator_bounds(tile_x, tile_y, zoom)`

Convert Tile Coordinates to Web Mercator bounds of the Tile.