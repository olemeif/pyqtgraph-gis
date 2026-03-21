import pyqtgraph as pg
import requests
from PyQt6 import QtCore, QtWidgets
from math import log

from numpy import ndarray

from .utils import (
    latlon_to_web_mercator,
    vectorized_wgs84_to_wm,
    vectorized_wm_to_wgs84,
    web_mercator_to_tile_coords,
    tile_coords_to_web_mercator_bounds,
    TILE_SIZE,
    TileWorker,
    LatLonAxis
)

__all__ = ['MapWidget']


class MapWidget(pg.PlotWidget):
    # Signal that emits (latitude, longitude)
    sigMapClicked = QtCore.pyqtSignal(float, float)
    sigMouseMoved = QtCore.pyqtSignal(float, float)

    def __init__(
            self,
            tile_server_url: str,
            headers: str | None = None,
            parent: QtCore.QObject | None = None,
            attribution_text: str | None = None,
            **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.tile_cache = {}  # Stores NumPy arrays of tile images
        self.current_tiles = {}  # Stores { (z, x, y): ImageItem }
        self.pending_tiles = set()  # Track tiles currently being loaded

        self.tile_server_url = tile_server_url
        self.headers = headers or {}
        self.session = requests.Session()  # Use a session for connection pooling

        self.setAxisItems({
            'bottom': LatLonAxis('bottom', is_lat=False),
            'left': LatLonAxis('left', is_lat=True)
        })

        self.current_tile_zoom = None

        # Connect proxy for mouse move (performance optimized)
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)

        self.threadpool = QtCore.QThreadPool()
        self.threadpool.setMaxThreadCount(8)

        self.setAspectLocked(True)
        view_box = self.getViewBox()
        view_box.sigRangeChanged.connect(self.update_map_tiles)

        # Prevent panning/zooming way outside the valid map area
        world_half_width_wm = 20037508.342789244
        view_box.setLimits(
            xMin=-world_half_width_wm,
            xMax=world_half_width_wm,
            yMin=-world_half_width_wm,
            yMax=world_half_width_wm,
            minXRange=1000,  # Prevent zooming in so far the math breaks
            minYRange=1000
        )

        initial_lat, initial_lon = 48.1351, 11.5820  # Munich
        initial_wm_x, initial_wm_y = latlon_to_web_mercator(initial_lat, initial_lon)

        initial_zoom = 12
        span_wm = 50_000
        self.setXRange(initial_wm_x - span_wm, initial_wm_x + span_wm, padding=0)
        self.setYRange(initial_wm_y - span_wm, initial_wm_y + span_wm, padding=0)

        # Attribution label
        if attribution_text:
            self.attribution_label = QtWidgets.QLabel(self)
            self.attribution_label.setText(attribution_text)

            # Allow links to be clickable
            self.attribution_label.setOpenExternalLinks(True)

            # Style it to look like a small, semi-transparent overlay
            self.attribution_label.setStyleSheet("""
                        QLabel {
                            background-color: rgba(255, 255, 255, 255);
                            color: #333;
                            padding: 2px 6px;
                            border-radius: 4px;
                            font-size: 10px;
                        }
                    """)
            self.attribution_label.adjustSize()

        self.update_map_tiles()

    def _tile_downloaded(self, tile_key, img_array):
        """Slot to handle a successfully downloaded tile."""
        self.tile_cache[tile_key] = img_array
        self.pending_tiles.discard(tile_key)
        self._add_tile_to_plot(tile_key, img_array)

    def _tile_error(self, error_info):
        """Slot to handle a tile download error."""
        tile_key, error_msg = error_info
        print(
            f"Error loading tile {tile_key}: {error_msg}")  # TODO: Remove this print statement and add proper error handling
        self.pending_tiles.discard(tile_key)

    def _add_tile_to_plot(self, tile_key, img_array):
        """Add a tile ImageItem to the plot."""
        z, x, y = tile_key
        if tile_key in self.current_tiles:
            return  # Tile is already on the plot

        tile_item = pg.ImageItem(img_array, antialias=True, levels=(0, 255))

        wm_x1, wm_y1, wm_x2, wm_y2 = tile_coords_to_web_mercator_bounds(x, y, z)
        tile_item.setRect(QtCore.QRectF(wm_x1, wm_y1, wm_x2 - wm_x1, wm_y2 - wm_y1))
        tile_item.setZValue(-100 - z)  # Deeper Zoom levels on top
        self.addItem(tile_item)
        self.current_tiles[tile_key] = tile_item

    def update_map_tiles(self):
        view_box = self.getViewBox()
        x_range, y_range = view_box.viewRange()

        widget_width_pixels = max(1, self.width())
        widget_height_pixels = max(1, self.height())
        world_width_wm = 2 * 20037508.342789244

        # Calculate ideal zoom level based on current view width
        current_view_width_wm = x_range[1] - x_range[0]
        meters_per_pixel_view = current_view_width_wm / widget_width_pixels

        ideal_zoom = log(world_width_wm / (TILE_SIZE * meters_per_pixel_view), 2)

        if self.current_tile_zoom is None:
            self.current_tile_zoom = round(ideal_zoom)
        else:
            # Get boxing zoom level to prevent excessive tile loading during fast zooms
            if abs(ideal_zoom - self.current_tile_zoom) > 1.5:
                self.current_tile_zoom = round(ideal_zoom)
            # Reduced hysteresis
            elif ideal_zoom > self.current_tile_zoom + 0.1:
                self.current_tile_zoom += 1
            elif ideal_zoom < self.current_tile_zoom - 0.1:
                self.current_tile_zoom -= 1

        # Keep zoom level within valid bounds (0-19 for most tile servers)
        self.current_tile_zoom = max(0, min(19, self.current_tile_zoom))
        current_zoom = self.current_tile_zoom

        # Target view size in Web Mercator at the current zoom level
        target_mpp = world_width_wm / (TILE_SIZE * (2 ** current_zoom))
        target_view_width = target_mpp * widget_width_pixels
        target_view_height = target_mpp * widget_height_pixels

        center_x = (x_range[0] + x_range[1]) / 2
        center_y = (y_range[0] + y_range[1]) / 2

        # Only correct view if deviation from target view size is more than 1%
        deviation = abs(current_view_width_wm - target_view_width) / target_view_width

        if deviation > 0.01:
            view_box.blockSignals(True)
            self.setXRange(
                center_x - target_view_width / 2,
                center_x + target_view_width / 2,
                padding=0
            )
            self.setYRange(
                center_y - target_view_height / 2,
                center_y + target_view_height / 2,
                padding=0
            )
            view_box.blockSignals(False)

            # Calculate new range for tile loading based on target view size
            min_wm_x = center_x - target_view_width / 2
            max_wm_x = center_x + target_view_width / 2
            min_wm_y = center_y - target_view_height / 2
            max_wm_y = center_y + target_view_height / 2
        else:
            # If deviation is small, use current view range for tile loading to avoid unnecessary corrections
            min_wm_x, max_wm_x = x_range
            min_wm_y, max_wm_y = y_range

        # Tile coordinates for the current view range
        tx1, ty1 = web_mercator_to_tile_coords(min_wm_x, min_wm_y, current_zoom)
        tx2, ty2 = web_mercator_to_tile_coords(max_wm_x, max_wm_y, current_zoom)

        tile_x_min = max(0, min(tx1, tx2))
        tile_x_max = min((2 ** current_zoom) - 1, max(tx1, tx2))
        tile_y_min = max(0, min(ty1, ty2))
        tile_y_max = min((2 ** current_zoom) - 1, max(ty1, ty2))

        newly_visible_tiles_key = set()
        tiles_to_remove = set(self.current_tiles.keys())

        for x in range(tile_x_min, tile_x_max + 1):
            for y in range(tile_y_min, tile_y_max + 1):
                tile_key = (current_zoom, x, y)
                newly_visible_tiles_key.add(tile_key)

                if tile_key in self.tile_cache:
                    self._add_tile_to_plot(tile_key, self.tile_cache[tile_key])
                    tiles_to_remove.discard(tile_key)
                elif tile_key not in self.current_tiles and tile_key not in self.pending_tiles:
                    self.pending_tiles.add(tile_key)

                    worker = TileWorker(current_zoom, x, y, self.tile_server_url, self.headers, self.session)
                    worker.signals.result.connect(self._tile_downloaded)
                    worker.signals.error.connect(self._tile_error)
                    self.threadpool.start(worker)
                else:
                    tiles_to_remove.discard(tile_key)

        # Remove tiles that are no longer visible
        for tile_key in tiles_to_remove:
            tile_item = self.current_tiles.pop(tile_key)
            self.removeItem(tile_item)

    def plot(self, lats: list, lons: list, *args, **kwargs):
        """
        Plots lines or curves using WGS84 coordinates.
        Returns the pg.PlotDataItem.
        """
        x, y = vectorized_wgs84_to_wm(lats, lons)
        return super().plot(x, y, *args, **kwargs)

    def scatter(self, lats: list, lons: list, **kwargs):
        """
        Adds a scatter plot using WGS84 coordinates.
        Returns the pg.ScatterPlotItem.
        """
        x, y = vectorized_wgs84_to_wm(lats, lons)
        scatter_item = pg.ScatterPlotItem(x=x, y=y, **kwargs)
        self.addItem(scatter_item)
        return scatter_item

    def image(self, image_data: ndarray, min_lat: float, min_lon: float, max_lat: float, max_lon: float,
                     **kwargs):
        """
        Overlays 2D array data (like a heatmap) given its WGS84 bounding box.
        Returns the pg.ImageItem.
        """
        # Convert bounding box to Web Mercator
        min_x, min_y = vectorized_wgs84_to_wm(min_lat, min_lon)
        max_x, max_y = vectorized_wgs84_to_wm(max_lat, max_lon)

        # Create the image item
        img_item = pg.ImageItem(image_data, **kwargs)

        # Scale and position the image to fit the Web Mercator bounds
        rect = QtCore.QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        img_item.setRect(rect)

        # Ensure the heatmap draws on top of the base map but below UI elements
        img_item.setZValue(10)

        self.addItem(img_item)
        return img_item

    def resizeEvent(self, event):
        """Keep the attribution label anchored to the bottom right."""
        super().resizeEvent(event)

        if hasattr(self, 'attribution_label'):
            # Define a small margin from the edges
            margin_x = 10
            margin_y = 30

            # Calculate new position
            new_x = self.width() - self.attribution_label.width() - margin_x
            new_y = self.height() - self.attribution_label.height() - margin_y

            self.attribution_label.move(new_x, new_y)

    def mousePressEvent(self, event):
        """Handle mouse clicks to emit WGS84 coordinates."""
        # Get the point in the ViewBox coordinate system (Web Mercator)
        scene_pos = QtCore.QPointF(event.pos())
        if self.getViewBox().sceneBoundingRect().contains(scene_pos):
            mouse_point = self.getViewBox().mapSceneToView(scene_pos)

            lat, lon = vectorized_wm_to_wgs84(mouse_point.x(), mouse_point.y())
            self.sigMapClicked.emit(lat, lon)

        super().mousePressEvent(event)

    def mouseMoved(self, evt):
        """Handle mouse movement to show live coordinates."""
        pos = evt[0]
        if self.getViewBox().sceneBoundingRect().contains(pos):
            mouse_point = self.getViewBox().mapSceneToView(pos)
            lat, lon = vectorized_wm_to_wgs84(mouse_point.x(), mouse_point.y())
            self.sigMouseMoved.emit(lat, lon)
