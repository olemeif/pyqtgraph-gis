import pyqtgraph as pg
import numpy as np
from math import log, tan, pi, atan, exp
from PyQt6 import QtCore, QtGui
from PyQt6.QtCore import pyqtSignal, pyqtSlot
import requests

TILE_SIZE = 256
pg.setConfigOption('useOpenGL', True)  # Enable OpenGL for better performance
pg.setConfigOption('antialias', True)  # Enable antialiasing for smoother tiles


def latlon_to_web_mercator(lat, lon):
    R = 6378137
    x = R * np.radians(lon)
    y = R * log(tan(pi / 4 + np.radians(lat) / 2))
    return x, y


def vectorized_wgs84_to_wm(lats, lons):
    """
    Vectorized conversion from WGS84 (Lat/Lon) to Web Mercator.
    Accepts scalar values, lists, or NumPy arrays.
    """
    lats = np.asarray(lats)
    lons = np.asarray(lons)

    r = 6378137.0  # Earth radius in meters
    x = r * np.radians(lons)
    y = r * np.log(np.tan(np.pi / 4.0 + np.radians(lats) / 2.0))

    return x, y


def web_mercator_to_latlon(x, y):
    R = 6378137
    lon = np.degrees(x / R)
    lat = np.degrees(2 * atan(exp(y / R)) - pi / 2)
    return lat, lon


def vectorized_wm_to_wgs84(x, y):
    """
    Converts Web Mercator (x, y) back to WGS84 (Lat/Lon).
    """
    x = np.asarray(x)
    y = np.asarray(y)

    r = 6378137.0
    lon = np.degrees(x / r)
    lat = np.degrees(2.0 * np.arctan(np.exp(y / r)) - np.pi / 2.0)

    return lat, lon


def web_mercator_to_tile_coords(x, y, zoom):
    map_size = TILE_SIZE * (2 ** zoom)
    max_extent = 20037508.342789244
    normalized_x = (x + max_extent) / (2 * max_extent)
    normalized_y = (max_extent - y) / (2 * max_extent)
    pixel_x = normalized_x * map_size
    pixel_y = normalized_y * map_size
    tile_x = int(pixel_x // TILE_SIZE)
    tile_y = int(pixel_y // TILE_SIZE)
    return tile_x, tile_y


def tile_coords_to_web_mercator_bounds(tile_x, tile_y, zoom):
    max_extent = 20037508.342789244
    map_size = TILE_SIZE * (2 ** zoom)
    pixel_x_tl = tile_x * TILE_SIZE
    pixel_y_tl = tile_y * TILE_SIZE
    wm_x_tl = (pixel_x_tl / map_size) * (2 * max_extent) - max_extent
    wm_y_tl = max_extent - (pixel_y_tl / map_size) * (2 * max_extent)
    pixel_x_br = (tile_x + 1) * TILE_SIZE
    pixel_y_br = (tile_y + 1) * TILE_SIZE
    wm_x_br = (pixel_x_br / map_size) * (2 * max_extent) - max_extent
    wm_y_br = max_extent - (pixel_y_br / map_size) * (2 * max_extent)
    return wm_x_tl, wm_y_br, wm_x_br, wm_y_tl


class TileSignals(QtCore.QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(tuple, np.ndarray)


class TileWorker(QtCore.QRunnable):
    def __init__(self, z, x, y, tile_server_url, headers, session):
        super().__init__()
        self.z = z
        self.x = x
        self.y = y
        self.tile_server_url = tile_server_url
        self.headers = headers
        self.session = session  # Use a shared requests session
        self.signals = TileSignals()

    @pyqtSlot()
    def run(self):
        tile_key = (self.z, self.x, self.y)
        url = self.tile_server_url.format(z=self.z, x=self.x, y=self.y)
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            image_data = response.content
            qimage = QtGui.QImage()
            qimage.loadFromData(image_data)

            if qimage.isNull():
                raise ValueError(f"Failed to load image data from {url}")

            qimage = qimage.convertToFormat(QtGui.QImage.Format.Format_ARGB32_Premultiplied)

            # Convert QImage to numpy array
            # This array is likely in BGRA format, so we need to convert it to RGBA
            img_array = pg.imageToArray(qimage, copy=True)
            img_array_reordered = img_array[..., [2, 1, 0, 3]]  # Convert BGRA to RGBA
            img_array_flipped = img_array_reordered[:, ::-1, :]  # Flip image

            self.signals.result.emit(tile_key, img_array_flipped)
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching tile {url}"
            if hasattr(e, "response") and e.response is not None and e.response.status_code:
                error_msg += f" (HTTP {e.response.status_code})"
                if e.response.status_code == 403:
                    error_msg += "\n Likely cause: Tile Usage Policy violation"
            self.signals.error.emit((tile_key, error_msg))
        except Exception as e:
            self.signals.error.emit((tile_key, f"Unexpected error: {str(e)}"))
        finally:
            self.signals.finished.emit()


class LatLonAxis(pg.AxisItem):
    def __init__(self, orientation, is_lat):
        super().__init__(orientation=orientation)
        self.is_lat = is_lat

    def tickStrings(self, values, scale, spacing):
        labels = []
        for v in values:
            lat, lon = web_mercator_to_latlon(
                0 if self.is_lat else v,
                v if self.is_lat else 0
            )
            labels.append(f"{lat if self.is_lat else lon:.4f}°")
        return labels
