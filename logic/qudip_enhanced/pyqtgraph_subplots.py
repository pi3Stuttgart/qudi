import sys

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Some random data for scatter plot
    x = np.random.normal(size=1000)
    y = np.random.normal(size=1000)

    # Create layout to hold multiple subplots
    pg_layout = pg.GraphicsLayoutWidget()

    # Add subplots
    pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=0, col=0, title="Plot @ row 1, column 1")
    pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=0, col=1, title="Plot @ row 1, column 2")
    pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=0, col=2, title="Plot @ row 1, column 3")
    pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=1, col=0, title="Plot @ row 2, column 1")
    pg_layout.addPlot(x=x, y=y, pen=None, symbol='x', row=2, col=0, title="Plot @ row 3, column 1")

    # Show our layout holding multiple subplots
    pg_layout.show()

    status = app.exec_()
    sys.exit(status)