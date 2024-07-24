import sys
import os

import numpy as np

from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.figure import Figure
import scipy.stats as stats
import glob

def find_major_axis(cplx: np.ndarray):
    """Find major axis from complex data
    
    Find major axis from complex data and return the angle indicating the direction of major axis
    
    Args:
        cplx (np.ndarray(complex)): IQ data as complex number
        
    Return:
        theta: angle of the major axis
        
    """
    X = np.stack((cplx.real, cplx.imag), axis=0)
    cov = np.cov(X, bias=0)
    eigval, eigvec = np.linalg.eig(cov)
    idx = np.argmin(eigval)
    theta = np.arctan2(eigvec[idx, 0], eigvec[idx, 1])
    return theta

def plot_noise(data, axes):
    theta = find_major_axis(data)
    pca = data*np.exp(-1j*theta)
    
    ax_t, ax_iq, ax_qq_major, ax_qq_minor = axes
    vlim = max(max(np.abs(data.real)), max(np.abs(data.imag)))
    ax_t.plot(np.arange(len(data)), data.real, "-", color="C0", alpha=0.7)
    ax_t.plot(np.arange(len(data)), data.imag, "-", color="C1", alpha=0.7)
    ax_iq.set_xlim(-vlim, vlim)
    ax_iq.set_ylim(-vlim, vlim)
    ax_iq.set_xlabel('I')
    ax_iq.set_ylabel('Q')
    ax_iq.set_aspect('equal')
    ax_iq.plot(data.real, data.imag, "o", alpha=0.2, markersize=1)
    ax_iq.plot([-vlim*np.cos(theta), vlim*np.cos(theta)], [-vlim*np.sin(theta), vlim*np.sin(theta)], "--", color="red")
    stats.probplot(pca.real, plot=ax_qq_major)
    ax_qq_major.set_title("Major axis")
    stats.probplot(pca.imag, plot=ax_qq_minor)
    ax_qq_minor.set_title("Minor axis")

class ApplicationWindow(QtWidgets.QMainWindow):
    def __init__(self, data_dir):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        canvas = FigureCanvas(Figure(figsize=(16, 8)))
        layout.addWidget(NavigationToolbar(canvas, self))
        layout.addWidget(canvas)

        capture_0_files = glob.glob(f"./{data_dir}/capture_0_*.npy")
        capture_0_files.sort(key=os.path.getmtime)
        data0 = np.load(capture_0_files[-1])
        capture_1_files = glob.glob(f"./{data_dir}/capture_1_*.npy")
        capture_1_files.sort(key=os.path.getmtime)
        data1 = np.load(capture_1_files[-1])

        fig = canvas.figure
        (axes0, axes1) = fig.subplots(2, 4)
        plot_noise(data0, axes0)
        plot_noise(data1, axes1)
        fig.tight_layout()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('data_dir', type=str)
    args = parser.parse_args()
    
    qapp = QtWidgets.QApplication.instance()
    if not qapp:
        qapp = QtWidgets.QApplication(sys.argv)

    app = ApplicationWindow(args.data_dir)
    app.show()
    app.activateWindow()
    app.raise_()
    qapp.exec()