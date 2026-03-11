Follow these steps to get your mapping environment running from scratch.

![Image showing the result of this Setup Guide - A PyQt6 Window with a PyQtGraph Plot Widget as a Map](https://github.com/user-attachments/assets/507a4bb2-d949-45b0-95fd-b55db21417bc)

## Create a Virtual Environment
It is highly recommended to use a virtual environment to avoid version conflicts between PyQt6 and other Qt-based tools.

```Bash
# Create the environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate
```

## Install PyQtGraph-GIS

```Bash
pip install PyQt6 pyqtgraph pyqtgraph-gis
```

## Implementation

Create a python file for your script.

For this guide we will use [OpenStreetMap](https://www.openstreetmap.org/) as our tile provider.

!!! warning "Important"
    When using OpenStreetMap as the tile provider it is very important to include a custom User-Agent and an attribution text, as per their [Usage Policy](https://operations.osmfoundation.org/policies/tiles/).

```Python
from pyqtgraph_gis import MapWidget
from PyQt6 import QtWidgets

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    w = QtWidgets.QWidget()

    # Required for OSM Tile Server compliance
    headers = {
        "User-Agent": "MyMapApp/1.0 (contact: email@example.com)"
    }

    w.setWindowTitle("PyQtGraph GIS")
    layout = QtWidgets.QGridLayout()
    w.setLayout(layout)

    # Initialize the map with OSM tiles and proper attribution
    widget = MapWidget(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png", 
        headers=headers,
        attribution_text='© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    )

    # Add a marker (e.g., North Cape)
    # Coordinates are [Latitude], [Longitude]
    north_cape = widget.add_scatter([71.1725], [25.784444], symbol="o", size=10, brush="r")

    layout.addWidget(widget, 0, 0)
    w.show()
    app.exec()
```