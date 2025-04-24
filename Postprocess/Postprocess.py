#Author Pierre Kuna

import os

os.environ["QT_PLUGIN_PATH"] = r"C:\Users\User\anaconda3\Library\plugins"

import re
import ast
import random
import json
import csv
from itertools import combinations, product
import copy
import sqlite3

import numpy as np
import pandas as pa
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.colorbar import Colorbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from lmfit import Model, Parameters
import pyqtgraph as pg
from scipy.signal import find_peaks,peak_widths
import seaborn as sns

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QCheckBox, QWidget, QLabel, QSplitter, QTextEdit, QSlider,
    QSpinBox, QProgressBar, QFileDialog, QStackedWidget, QTabWidget, QListWidget, QTreeView,
    QAbstractItemView, QPlainTextEdit, QInputDialog, QMessageBox,QMenu
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QPalette, QPixmap,QIcon,QKeySequence
from PyQt5.QtCore import Qt, QRegExp,Signal

sns.set_context("paper")
sns.set(font_scale=1, style='white')
sns.set_style("ticks", {"xtick.major.size": 2.5, "ytick.major.size": 0, "xtick.direction": "in"})

cmap = sns.color_palette("colorblind")

class TabWidget(QTabWidget):

    tabRemovedSignal = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Enable custom context menu on the tab bar
        self.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self.show_context_menu)

    def removeTab(self, index):
        # Call the original removeTab method to remove the tab.
        # Emit our custom signal after the tab is removed.
        self.tabRemovedSignal.emit(index)
        super().removeTab(index)

    def show_context_menu(self, pos):
        # Get the index of the tab under the mouse pointer
        tab_index = self.tabBar().tabAt(pos)
        if tab_index < 0:
            return  # No tab was clicked

        # Create the context menu
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Tab")
        # Map the local position to global screen coordinates
        global_pos = self.tabBar().mapToGlobal(pos)
        action = menu.exec_(global_pos)

        # If the delete action was triggered, remove the tab
        if action == delete_action:
            self.removeTab(tab_index)

class EnhancedTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            selected = self.selectedItems()
            if selected:
                copied_text = []
                for item in selected:
                    base = item.text()
                    extra = item.toolTip()
                    copied_text.append(f"{base} (+-{extra})" if extra else base)
                clipboard_text = "\n".join(copied_text)
                QApplication.clipboard().setText(clipboard_text)
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class SQLiteHistoryManager:
    def __init__(self, db_path="history.db", max_size=100):
        self.db_path = db_path
        self.max_size = max_size
        self._initialize_db()

    def _initialize_db(self):
        """Set up the database table for history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _get_last_entry(self):
        """Retrieve the most recent entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT input FROM history ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None

    def is_identical_to_last(self, user_input):
        """Check if the input is identical to the last entry."""
        last_input = self._get_last_entry()
        return last_input == user_input

    def _trim_history(self):
        """Ensure the history size remains within the limit."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM history
                WHERE id NOT IN (
                    SELECT id FROM history
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (self.max_size,))
            conn.commit()

    def add_input(self, user_input):
        """Add a new input to the history if it's not a duplicate."""
        if not self.is_identical_to_last(user_input):
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO history (input) VALUES (?)", (user_input,))
                conn.commit()
            self._trim_history()

    def search(self, keyword):
        """Search for inputs containing a keyword."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT input FROM history WHERE input LIKE ?", (f"%{keyword}%",))
            return [row[0] for row in cursor.fetchall()]

    def get_last(self, n=1):
        """Retrieve the last n inputs."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT input FROM history ORDER BY id DESC LIMIT ?", (n,))
            return [row[0] for row in cursor.fetchall()]

    def get_count(self):
        """Return the total number of inputs in the history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM history")
            return cursor.fetchone()[0]

    def get_element_by_index(self, index):
        """Retrieve a specific history element by its index (0-based)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT input FROM history
                ORDER BY id ASC
                LIMIT 1 OFFSET ?
            """, (index,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return ""


class NonLazyFileModel(QStandardItemModel):
    def __init__(self, root_path,progress_bar, parent=None):
        self.progress_bar = progress_bar
        super().__init__(parent)
        self.setHorizontalHeaderLabels(['Name'])  # Only one column for Name
        self.load_directory(root_path)

    def load_directory(self, root_path):
        """
        Load the entire directory structure starting from `root_path`.
        """
        root_item = self.invisibleRootItem()
        self._add_items(root_item, root_path)

    def _add_items(self, parent_item, path):
        """
        Recursively add directory and file items to the model.
        """
        self.progress_bar.setRange(0, 0)
        try:

            for entry in os.scandir(path):
                item = QStandardItem(entry.name)
                item.setEditable(False)
                item.setData(entry.path, Qt.UserRole)  # Store the full path
                parent_item.appendRow(item)

                if entry.is_dir():
                    # Add a child row for directories
                    self._add_items(item, entry.path)

        except PermissionError:
            pass  # Skip directories without access

        self.progress_bar.setRange(0, 100)

def parse_parameters(expression):
    """
    Parse unique parameter names from the given expression.
    Exclude reserved variables (x, y, z) and identifiers prefixed with 'np.'.
    """
    pattern = r'\b(?:np\.)?[a-zA-Z_][a-zA-Z0-9_]*\b'
    matches = re.findall(pattern, expression)
    reserved_vars = {'x', 'y', 'z'}
    parameters = [
        param for param in matches
        if not param.startswith('np.') and param not in reserved_vars
    ]
    return list(parameters)


def extract_parameters(expr):
    """
    Parses the expression string and returns a tuple (params, uses_y).

    - 'params' is an ordered list of parameter names extracted from the expression,
      ignoring special names: 'x', 'np', and 'y'.
    - 'uses_y' is True if the expression explicitly references 'y'.
    """

    class ParameterExtractor(ast.NodeVisitor):
        def __init__(self):
            self.params = []
            self.uses_y = False

        def visit_Call(self, node):
            # Only traverse the arguments (ignore the function name itself)
            for arg in node.args:
                self.visit(arg)
            for kw in node.keywords:
                self.visit(kw)

        def visit_Attribute(self, node):
            # For an attribute (like np.sin), only traverse its value
            self.visit(node.value)

        def visit_Name(self, node):
            if node.id == 'y':
                self.uses_y = True
                return  # Do not add 'y' to parameters.
            if node.id in ('x', 'np'):
                return
            if node.id not in self.params:
                self.params.append(node.id)

    tree = ast.parse(expr, mode='eval')
    extractor = ParameterExtractor()
    extractor.visit(tree)
    return extractor.params, extractor.uses_y


def build_function(expr, func_name, safe_globals):
    """
    Given a literal expression and a function name, returns a callable function.

    The returned function supports two calling conventions:

      - If the expression uses 'y', then it must be called with (x, y, *extra_params).
      - If the expression does not use 'y', then it can be called either as:
          (x, *extra_params)  [for compound calls]
        or
          (x, y, *extra_params)  [for direct calls, in which case y is simply ignored].

    The extra parameters are determined by the order in which they first appear in the expression.
    """
    params, uses_y = extract_parameters(expr)

    def func(*fargs):
        if uses_y:
            # We require that the caller supplies both x and y.
            expected = len(params) + 2  # x, y, plus the extra parameters.
            if len(fargs) != expected:
                raise ValueError(
                    f"Function '{func_name}' expects {expected} arguments (x, y, and parameters {params}), got {len(fargs)}."
                )
            x = fargs[0]
            y = fargs[1]
            args_for_params = fargs[2:]
            local_vars = {'x': x, 'y': y, 'np': np}
        else:
            # If 'y' is not used in the expression, allow both:
            #   compound calls:  f(x, *params)
            #   direct calls:    f(x, y, *params)
            if len(fargs) == len(params) + 1:
                # Compound call: only x is provided.
                x = fargs[0]
                args_for_params = fargs[1:]
                local_vars = {'x': x, 'np': np}
            elif len(fargs) == len(params) + 2:
                # Direct call: both x and y are provided; we ignore y in the eval.
                x = fargs[0]
                y = fargs[1]
                args_for_params = fargs[2:]
                local_vars = {'x': x, 'y': y, 'np': np}
            else:
                raise ValueError(
                    f"Function '{func_name}' expects either {len(params) + 1} or {len(params) + 2} arguments (x, [y,] and parameters {params}), got {len(fargs)}."
                )
        # Map each extracted parameter to its corresponding passed value.
        for name, value in zip(params, args_for_params):
            local_vars[name] = value
        return eval(expr, safe_globals, local_vars)

    # Attach metadata for debugging or introspection.
    func.param_order = params
    func.uses_y = uses_y
    return func

class FitManager:
    def __init__(self):
        self.fits = {}
        self.predefined_functions = {}
        self.fit_parameters={}
        self.lines=[]
        self.functions={"np":np} #this will be the globals when trying to exec the function

        if os.path.isfile("fit_functions.txt"):
            fi=open("fit_functions.txt","r")
            self.lines=fi.readlines()
            fi.close()
            for line in self.lines:
                arguments=line[:-1].split("|")
                self.add_fit_function(*arguments)

        else:
            self.add_fit_function("sine", "a * np.sin(b * x) + c")
            self.add_fit_function("cosine", "a * np.cos(b * x) + c")
            self.add_fit_function("exp_decay", "d * np.exp(-e * x)")
            self.add_fit_function("2d_contour", "a * x ** 2 + b * y ** 2 + c * x * y + d * x + e * y + f")
            self.add_fit_function("exponential", "a * np.exp(b * x) + c")
            self.add_fit_function("logarithmic", "a * np.log(b * x) + c")
            self.add_fit_function("linear", "a * x + b")
            self.add_fit_function("quadratic", "a * x**2 + b * x + c")
            self.add_fit_function("cubic", "a * x**3 + b * x**2 + c * x + d")
            self.add_fit_function("gaussian", "a * np.exp(-((x - b)**2) / (2 * c**2))")
            self.add_fit_function("lorentzian", "a / (1 + ((x - b) / c)**2)")
            self.add_fit_function("power_law", "a * x**b + c")
            self.add_fit_function("sigmoid", "a / (1 + np.exp(-b * (x - c)))")
            self.add_fit_function("hyperbolic_tangent", "a * np.tanh(b * x) + c")
            self.add_fit_function("rectangular", "a * (np.abs(x) <= b)")
            self.add_fit_function("heaviside", "a * (x >= b)")
            self.add_fit_function("step", "a * (x >= b) + c")
            self.add_fit_function("damped_sine", "a * np.exp(-b * x) * np.sin(c * x + d)")
            self.add_fit_function("fourier_series", "a0 + a1 * np.cos(omega * x) + b1 * np.sin(omega * x)")
            self.add_fit_function("logistic_growth", "L / (1 + np.exp(-k * (x - x0)))")
            self.add_fit_function("weibull", "(a / b) * (x / b)**(a - 1) * np.exp(-(x / b)**a)")
            self.add_fit_function("gamma", "(x**(a - 1) * np.exp(-x / b)) / (b**a * gamma(a))")
            self.add_fit_function("polynomial_4th", "a*x**4 + b*x**3 + c*x**2 + d*x + e")
            self.add_fit_function("double_exponential", "a * np.exp(-b * x) + c * np.exp(-d * x)")
            self.add_fit_function("softplus", "a * np.log(1 + np.exp(b * x)) + c")
            #self.add_fit_function("erf", "a * scipy.special.erf(b * (x - c))")
            #self.add_fit_function("bessel", "a * scipy.special.jn(n, b * x)")


    def guess_parameters(self,function_name, x, y):
        """
        Generate initial guesses for parameters of a given fitting function.

        Parameters:
        - function_name (str): Name of the fitting function.
        - x (np.array): Independent variable.
        - y (np.array): Dependent variable.

        Returns:
        - dict: A dictionary with parameter names as keys and initial guesses as values.
        """
        initial_guesses = {}

        if function_name == "sine":
            initial_guesses = {
                "a": (np.max(y) - np.min(y)) / 2,  # Amplitude
                "b": 2 * np.pi / (x[np.argmax(np.gradient(np.sign(np.gradient(y))))] - x[0]),  # Frequency
                "c": np.mean(y),  # Offset
            }
        elif function_name == "cosine":
            initial_guesses = {
                "a": (np.max(y) - np.min(y)) / 2,  # Amplitude
                "b": 2 * np.pi / (x[np.argmax(np.gradient(np.sign(np.gradient(y))))] - x[0]),  # Frequency
                "c": np.mean(y),  # Offset
            }
        elif function_name == "exp_decay":
            initial_guesses = {
                "d": np.max(y),  # Initial amplitude
                "e": 1 / (x[-1] - x[0]),  # Decay rate
            }
        elif function_name == "2d_contour":
            initial_guesses = {k: 1.0 for k in ["a", "b", "c", "d", "e", "f"]}  # Default to 1.0
        elif function_name == "exponential":
            initial_guesses = {
                "a": y[0] - np.min(y),  # Initial amplitude
                "b": 1 / (x[-1] - x[0]),  # Exponential growth/decay rate
                "c": np.min(y),  # Offset
            }
        elif function_name == "logarithmic":
            initial_guesses = {
                "a": 1.0,
                "b": 1.0,
                "c": np.min(y),
            }
        elif function_name == "linear":
            slope, intercept = np.polyfit(x, y, 1)
            initial_guesses = {"a": slope, "b": intercept}
        elif function_name == "quadratic":
            coeffs = np.polyfit(x, y, 2)
            initial_guesses = {"a": coeffs[0], "b": coeffs[1], "c": coeffs[2]}
        elif function_name == "cubic":
            coeffs = np.polyfit(x, y, 3)
            initial_guesses = {"a": coeffs[0], "b": coeffs[1], "c": coeffs[2], "d": coeffs[3]}
        elif function_name == "gaussian":
            initial_guesses = {
                "a": np.max(y),
                "b": x[np.argmax(y)],
                "c": (x[-1] - x[0]) / 6,  # Rough FWHM estimate
            }
        elif function_name == "lorentzian":
            initial_guesses = {
                "a": np.max(y),
                "b": x[np.argmax(y)],
                "c": (x[-1] - x[0]) / 10,
            }
        elif function_name == "power_law":
            initial_guesses = {"a": 1.0, "b": 1.0, "c": np.min(y)}
        elif function_name == "sigmoid":
            initial_guesses = {
                "a": np.max(y),
                "b": 1.0,
                "c": x[np.argmin(np.abs(y - np.mean(y)))],
            }
        elif function_name == "hyperbolic_tangent":
            initial_guesses = {
                "a": (np.max(y) - np.min(y)) / 2,
                "b": 1.0,
                "c": np.mean(y),
            }
        elif function_name == "rectangular":
            initial_guesses = {"a": np.max(y), "b": (x[-1] - x[0]) / 2}
        elif function_name == "heaviside":
            initial_guesses = {"a": np.max(y), "b": np.mean(x)}
        elif function_name == "step":
            initial_guesses = {"a": np.max(y), "b": np.mean(x), "c": np.min(y)}
        elif function_name == "damped_sine":
            initial_guesses = {
                "a": (np.max(y) - np.min(y)) / 2,
                "b": 1 / (x[-1] - x[0]),
                "c": 2 * np.pi / (x[np.argmax(np.gradient(np.sign(np.gradient(y))))] - x[0]),
                "d": 0.0,
            }
        elif function_name == "fourier_series":
            initial_guesses = {
                "a0": np.mean(y),
                "a1": (np.max(y) - np.min(y)) / 2,
                "b1": 0.0,
                "omega": 2 * np.pi / (x[-1] - x[0]),
            }
        elif function_name == "logistic_growth":
            initial_guesses = {
                "L": np.max(y),
                "k": 1.0,
                "x0": x[np.argmin(np.abs(y - np.max(y) / 2))],
            }
        elif function_name == "weibull":
            initial_guesses = {"a": 1.5, "b": np.mean(x)}
        elif function_name == "gamma":
            initial_guesses = {"a": 2.0, "b": np.mean(x)}
        elif function_name == "polynomial_4th":
            coeffs = np.polyfit(x, y, 4)
            initial_guesses = {"a": coeffs[0], "b": coeffs[1], "c": coeffs[2], "d": coeffs[3], "e": coeffs[4]}
        elif function_name == "double_exponential":
            initial_guesses = {
                "a": y[0],
                "b": 1 / (x[-1] - x[0]),
                "c": y[-1] - y[0],
                "d": 1 / (x[-1] - x[0]) * 2,
            }
        elif function_name == "softplus":
            initial_guesses = {"a": 1.0, "b": 1.0, "c": np.min(y)}

        return initial_guesses

    def smart_initial_guess(self,variable_names, x, y):
        """
        Generate smart initial guesses for fitting parameters based on variable names and x, y data.

        This function uses FFT analysis to estimate frequency components and finds both positive
        peaks and dips in the time-domain signal. When a variable name (e.g. "x0", "x1", etc.) is
        encountered, the corresponding extreme (peak or dip) is selected based on its rank in terms
        of absolute deviation from the mean.

        Parameters:
            variable_names (list of str): Names of the variables in the fitting function.
            x (numpy array): Independent variable data.
            y (numpy array): Dependent variable data.

        Returns:
            dict: A dictionary with variable names as keys and initial guesses as values.
        """
        # --- Preprocessing ---
        # Center y for frequency analysis.
        y_centered = y - np.mean(y)

        # Determine sampling rate from x.
        if len(x) > 1:
            sampling_rate = 1.0 / np.mean(np.diff(x))
        else:
            sampling_rate = 1.0
        N = len(y)

        # --- FFT Analysis ---
        fft_vals = np.fft.fft(y_centered)
        fft_freqs = np.fft.fftfreq(N, d=1.0 / sampling_rate)
        half = N // 2
        pos_freqs = fft_freqs[:half]
        pos_fft_vals = fft_vals[:half]
        pos_magnitudes = np.abs(pos_fft_vals)

        # Find peaks in the FFT magnitude (ignore very small peaks).
        fft_peak_inds, _ = find_peaks(pos_magnitudes, height=np.max(pos_magnitudes) * 0.1)
        if fft_peak_inds.size > 0:
            fft_peak_mags = pos_magnitudes[fft_peak_inds]
            # Sort FFT peaks by descending amplitude.
            sort_fft = np.argsort(fft_peak_mags)[::-1]
            fft_peak_inds_sorted = fft_peak_inds[sort_fft]
            # Corresponding frequencies:
            peak_freqs = pos_freqs[fft_peak_inds_sorted]
        else:
            fft_peak_inds_sorted = np.array([])
            peak_freqs = np.array([])

        # --- Time-Domain Extreme Analysis (Peaks and Dips) ---
        # Find positive peaks.
        pos_inds, _ = find_peaks(y)
        # Find dips by finding peaks in the inverted signal.
        neg_inds, _ = find_peaks(-y)
        # Combine the indices.
        all_extrema = np.concatenate((pos_inds, neg_inds))
        if all_extrema.size > 0:
            baseline = np.mean(y)
            # Rank extrema by absolute deviation from the baseline.
            ext_strength = np.abs(y[all_extrema] - baseline)
            sorted_extrema_inds = all_extrema[np.argsort(ext_strength)[::-1]]
        else:
            sorted_extrema_inds = np.array([])

        # --- Generate Initial Guesses ---
        initial_guesses = {}

        for var in variable_names:
            lower = var.lower()

            # --- Fourier-domain frequency parameters ---
            # Patterns like "f0", "w1", "omega_2", "frequency3", etc.
            m_fft = re.match(r'^(f|w|omega|frequency)[_]?(\d+)$', lower)
            if m_fft:
                idx = int(m_fft.group(2))
                if idx < len(peak_freqs):
                    initial_guesses[var] = peak_freqs[idx]
                else:
                    initial_guesses[var] = 0.0
                continue

            # Generic Fourier-frequency parameters (without digits).
            if lower in {"f", "w", "omega", "frequency"}:
                initial_guesses[var] = peak_freqs[0] if len(peak_freqs) > 0 else 0.0
                continue

            # --- Time-domain position parameters (e.g. x0, x1, etc.) ---
            # Here we use the ranked list of extrema (which can be peaks or dips).
            m_time = re.match(r'^x(\d+)$', lower)
            if m_time:
                idx = int(m_time.group(1))
                if idx < len(sorted_extrema_inds):
                    initial_guesses[var] = x[sorted_extrema_inds[idx]]
                else:
                    initial_guesses[var] = np.mean(x)
                continue

            # --- Amplitude parameters ---
            if lower in {"a", "amp", "amplitude"}:
                if sorted_extrema_inds.size > 0:
                    # Use the value at the most extreme point (peak or dip).
                    initial_guesses[var] = y[sorted_extrema_inds[0]]
                else:
                    initial_guesses[var] = np.ptp(y)
                continue

            # --- Phase parameters ---
            if lower in {"phi", "phase", "theta"}:
                if fft_peak_inds_sorted.size > 0:
                    initial_guesses[var] = np.angle(fft_vals[fft_peak_inds_sorted[0]])
                else:
                    initial_guesses[var] = 0.0
                continue

            # --- Offset parameters ---
            if lower in {"offset", "b", "o", "base", "baseline"}:
                initial_guesses[var] = np.mean(y)
                continue

            # --- Width parameters (e.g. sigma, s, delta, fwhm) ---
            if lower in {"sigma", "s", "delta", "fwhm"}:
                if sorted_extrema_inds.size > 0:
                    ext_idx = sorted_extrema_inds[0]
                    # Check if the extreme is a dip (value below baseline).
                    if y[ext_idx] < np.mean(y):
                        # For a dip, measure width from the inverted signal.
                        widths, _, _, _ = peak_widths(-y, [ext_idx], rel_height=0.5)
                    else:
                        widths, _, _, _ = peak_widths(y, [ext_idx], rel_height=0.5)
                    dx = x[1] - x[0] if len(x) > 1 else 1.0
                    initial_guesses[var] = widths[0] * dx
                else:
                    initial_guesses[var] = (x[-1] - x[0]) / 10.0
                continue

            # --- Period parameters (T, P) ---
            if lower in {"t", "p", "period"} or var in {"T", "P"}:
                if len(peak_freqs) > 0 and peak_freqs[0] > 0:
                    initial_guesses[var] = 1.0 / peak_freqs[0]
                else:
                    initial_guesses[var] = 0.0
                continue

            # --- Decay parameters ---
            if lower in {"tau", "gamma", "lambda"}:
                # An arbitrary guess based on data length and sampling rate.
                initial_guesses[var] = N / (sampling_rate * 10)
                continue

            # --- Harmonic parameters (e.g. h0, h1, k1, etc.) ---
            m_harm = re.match(r'^(h|k)(\d+)$', lower)
            if m_harm:
                idx = int(m_harm.group(2))
                # Use (index+1) times the fundamental frequency if available.
                if len(peak_freqs) > 0:
                    initial_guesses[var] = (idx + 1) * peak_freqs[0]
                else:
                    initial_guesses[var] = 0.0
                continue

            # --- Speed/distance parameters ---
            if lower in {"c", "d"}:
                initial_guesses[var] = np.max(y) - np.min(y)
                continue

            # --- Scaling or shape parameters ---
            if lower in {"alpha", "beta"}:
                if lower == "alpha":
                    initial_guesses[var] = np.var(y)
                else:  # for beta
                    initial_guesses[var] = (np.max(y) - np.min(y)) / 2.0
                continue

            # --- Central value for distributions ---
            if lower in {"mu"}:
                initial_guesses[var] = np.mean(y)
                continue

            # --- Default fallback ---
            initial_guesses[var] = 1.0

        return initial_guesses

    def get_smat_initial_guesses(self,fit_function,x,y,variable_names):
        res=self.guess_parameters(fit_function, x, y)
        if res=={}:
            res=self.smart_initial_guess(variable_names, x, y)

        return res

    def add_fit_function(self, name, expression, display_name=None):
        if name in self.fits:
            #print(f"Fit function '{name}' already exists.")
            return

        #function_calls = self.extract_function_calls(expression, self.predefined_functions)
        #modified_expression = self.replace_functions_with_literals(expression, function_calls,
        #                                                           self.predefined_functions)

        #parameters = parse_parameters(expression)

        modified_expression = expression.replace(" ", "")
        function_build=build_function(expression,name,self.functions)
        parameters = function_build.param_order
        self.fits[name] = {
            "expression": expression,
            "machine_expression": modified_expression,
            "parameters_blueprint": {
                param: {"initial_guess": 1.0, "fitted_value": None, "vary": True, "std":None}
                for param in parameters
            },
            "display_name": display_name or name,
            "parameters": {},
            "function":function_build
        }
        #self.predefined_functions[name] = modified_expression
        self.functions[name]=function_build
        self.fit_parameters[name] = self.fits[name]["parameters"]

        #save the new fit function
        self.lines=self.lines+["|".join([name,expression,display_name or name])+"\n"]
        fi=open("fit_functions.txt","w")
        fi.writelines(self.lines)
        fi.close()


    def prepare_parameters(self,parameter_combinations,overwrite=False): # ensures self.fits[name]["parameters"] is filled with fit parameters for the specified parameter combinations
        for name in self.fits: #for each fit function name
            for parameter_combination in parameter_combinations:
                if overwrite:
                    self.fit_parameters[name][parameter_combination] = copy.deepcopy(self.fits[name]["parameters_blueprint"])

                elif not parameter_combination in self.fit_parameters[name].keys(): # do not overwrite existing data
                    self.fit_parameters[name][parameter_combination]=copy.deepcopy(self.fits[name]["parameters_blueprint"])

            # clean up:
            to_remove=[]
            for combi in self.fit_parameters[name]:
                if combi not in parameter_combinations:
                    to_remove.append(combi)

            for combi in to_remove:
                del self.fit_parameters[name][combi]

    def list_display_names(self):
        return [self.fits[name]["display_name"] for name in self.fits]

class DataProcessor:
    def __init__(self,folder,progress_bar):
        self.data = {}  # Store x, y data
        self.fit_parameters = {}  # Store fit parameters in the same format as FitManager
        self.fit_results = {}  # Store fit results and parameters for each fit function
        self.folder=folder
        self.base_data=None
        self.N_lines=3
        self.fft_mode=False
        self.two_d = False
        self.progress_bar=progress_bar

        self.difference_param="__None__"
        self.x_axis_param="__None__"
        self.y_axis_param="__None__"
        self.z_axis_param="__None__"
        self.average_params=[]
        self.active_combinations=[]
        self.parameter_map=[]

        self.label_to_combi={}
        self.combi_to_label={}

        self.simultaneous_measurements = 0
        self.ana_seq = []
        self.indexes = []

        self.load_data()
        self.unselected={param:[] for param in self.measurement_parameters.keys()}
        self.fitted_params_df=pa.DataFrame()

    def load_data(self):
    
        try:
            if type(self.folder)!=type([]):
                self.folder=[self.folder]
            new=True
            for folder in self.folder:
                store = pa.HDFStore(os.path.join(folder,'data.hdf'))
                df = store['/df']

                #if getattr(store.get_storer("df").attrs, "Datatypes"):
                try:
                    for key in ["Datatypes"]:
                        print(1)
                        setattr(df, f"_{key}", getattr(store.get_storer("df").attrs, key))
                except Exception as e:
                    print(2,e)
                    for key in ["Datatypes"]:
                        setattr(df, f"_{key}", df.dtypes)

                df = df.astype(df._Datatypes)
                df["__None__"]=0

                added_observations=[]

                for col in df.columns:
                    if col.startswith("result_"):
                        df[f"recalculated_{col.replace('result_','')}"]=0.0#self.df[col]
                        added_observations.append(f"recalculated_{col.replace('result_','')}")

                for key in ["parameter_names","observation_names","dtypes"]:
                    setattr(df, f"_{key}", getattr(store.get_storer("df").attrs, key))

                try: #TODO do this more concisely
                    for key in ["Datatypes"]:
                        print(3)
                        setattr(df, f"_{key}", getattr(store.get_storer("df").attrs, key))
                except Exception as e:
                    print(4,e)
                    for key in ["Datatypes"]:
                        setattr(df, f"_{key}", df.dtypes)

                df._Datatypes["__None__"]=np.dtype("int16")
                store.close()

                if new:
                    self.df=df
                    new=False
                else:
                    if sorted(self.df.columns)==sorted(df.columns):
                        self.df=pa.concat([self.df,df])
                        for key in ["_parameter_names","_observation_names","_dtypes","_Datatypes"]:
                            setattr(self.df, f"{key}", getattr(df, key))

                    else:
                        # Create a question message box.
                        reply = QMessageBox.question(
                            None,                               # No parent widget
                            'Proceed?',                         # Title of the dialog
                            "the new and old dataframe have different columns. Proceed?",  # The message text
                            QMessageBox.Yes | QMessageBox.No,    # Buttons to display
                            QMessageBox.No                      # Default button
                        )
                        
                        # Check the user's response.
                        if reply == QMessageBox.Yes:
                            self.df=pa.concat([self.df,df])
                        else:
                            pass
                
                


        except Exception as e:
            store.close()
            print("Failed to load with HDFStore, trying a more primitive approach\nerror:",e)
            try:
                self.df = pa.read_hdf(os.path.join(self.folder,'data.hdf'))
                self.df["__None__"] = 0

                for i, trace in enumerate(self.df.trace):
                    try:
                        liste = list(map(int, re.findall(r'\d+', trace)))
                        self.df.trace[i] = np.array(liste, dtype=np.int16)
                    except Exception as e:
                        print(e)
                        pass


            except Exception as e:
                print("Failed to load the data. no data loaded\nerror",e)

        self.columns=self.df.columns
        self.measurement_parameters={name:self.df[name].unique() for name in self.df._parameter_names+["__None__"]}
        self.measurement_observations={name:self.df[name].unique() for name in self.df._observation_names+added_observations}

    def make_trace_to_list(self):
        def fix_and_convert_list(string):
            try:
                fixed=list(map(int, re.findall(r'\d+', trace)))
                return fixed
            except (ValueError, SyntaxError):
                return None  # Handle invalid strings

        traces = []
        for i, trace in enumerate(self.df.trace):
            traces.append(fix_and_convert_list(trace))
            self.progress_bar.setValue(int((i + 1) / len(self.df.trace) * 100))

        # self.df["Trace"]=self.df.trace.appy(fix_and_convert_list)
        self.df["Trace"] = traces

    def extract_data(self):
        def try_convert(val):
            try:
                return val.astype(float)
            except:
                return val

        if not (self.x_axis_param!="__None__" and self.x_axis_param!="__None__"):
            print("no x and y axis defined, please select these to be able to plot")
            return

        self.label_to_combi = {}
        self.combi_to_label = {}
        self.data = {}

        flag=False

        if (self.x_axis_param in self.fitted_params_df.columns) and (self.y_axis_param in self.fitted_params_df.columns):
            flag=True
            df=self.fitted_params_df
            difference_param="__None__" # do not allow difference to be applied extracting data from fitted df

        else:
            df=self.df
            difference_param=self.difference_param

        # Filter the DataFrame (only to exclude the x axis elements that were deselected
        for col, values in self.unselected.items():
            if col in df.columns:
                df = df[~df[col].isin(values)]  # Keep rows where column values are NOT in the unwanted list

        for combination in self.active_combinations:
            if not flag:
                if len(combination)!=len(self.parameter_map):
                    print("ERROR: parameter map or combination incomplete")
                    return

            # Dictionary with desired values
            desired_values = {self.parameter_map[i]:combination[i] for i in range(len(combination))}

            if flag:
                for key in [self.x_axis_param,self.y_axis_param,self.z_axis_param,self.difference_param,*self.average_params]:
                    if key in desired_values.keys():
                        try:
                            desired_values.pop(key)
                        except:
                            print("Error when cleaning desired values")

            # Filter for the parameters to match
            filtered_df = df.loc[(df[list(desired_values)] == pa.Series(desired_values)).all(axis=1)]

            if flag:
                filtered_df=filtered_df.apply(try_convert)


            label={key:desired_values[key] for key in desired_values.keys() if len(df[key].unique())>1 }
            # Convert the dictionary values to plain types
            cleaned_data = {key: str(value) if isinstance(value, (np.generic, np.number)) else str(value) for key, value
                            in label.items()}

            label = str(cleaned_data)[1:-1].replace("'","")

            self.label_to_combi[label] = combination
            self.combi_to_label[combination] = label

            if self.z_axis_param=="__None__":
                self.two_d=False
                if difference_param=="__None__":
                    prepared_df=filtered_df.groupby([self.x_axis_param], as_index=False).agg("mean", numeric_only=True)
                    x = np.array(prepared_df[self.x_axis_param])
                    y = np.array(prepared_df[self.y_axis_param])
                else:
                    prepared_df = filtered_df.groupby([self.x_axis_param,difference_param], as_index=False).agg("mean",
                                                                                               numeric_only=True)
                    x = np.array(prepared_df.loc[prepared_df[difference_param]==prepared_df[difference_param].unique()[0]][self.x_axis_param])
                    y = np.array(prepared_df.loc[prepared_df[difference_param]==prepared_df[difference_param].unique()[0]][self.y_axis_param])-np.array(prepared_df.loc[prepared_df[self.difference_param]==prepared_df[self.difference_param].unique()[1]][self.y_axis_param])


                self.data[combination] = (x, y, [])

            else: #2d plot
                self.two_d=True
                if difference_param == "__None__":
                    prepared_df=filtered_df.groupby([self.x_axis_param,self.y_axis_param], as_index=False).agg("mean", numeric_only=True)
                    grid= prepared_df.pivot(index=self.x_axis_param, columns=self.y_axis_param, values=self.z_axis_param)

                    x = grid.columns.values  # amp values
                    y = grid.index.values  # dur values
                    z = grid.values  # result_0 values

                    x, y = np.meshgrid(x, y)
                else:
                    filter_values1={difference_param:filtered_df[difference_param].unique()[0]}
                    filtered_df1=filtered_df.loc[(filtered_df[list(filter_values1)] == pa.Series(filter_values1)).all(axis=1)]
                    prepared_df1 = filtered_df1.groupby([self.x_axis_param, self.y_axis_param], as_index=False).agg("mean",
                                                                                                         numeric_only=True)
                    grid1 = prepared_df1.pivot(index=self.x_axis_param, columns=self.y_axis_param,
                                             values=self.z_axis_param)


                    filter_values2={difference_param:filtered_df[difference_param].unique()[1]}
                    filtered_df2=filtered_df.loc[(filtered_df[list(filter_values2)] == pa.Series(filter_values2)).all(axis=1)]
                    prepared_df2 = filtered_df2.groupby([self.x_axis_param, self.y_axis_param], as_index=False).agg("mean",
                                                                                                         numeric_only=True)
                    grid2 = prepared_df2.pivot(index=self.x_axis_param, columns=self.y_axis_param,
                                             values=self.z_axis_param)

                    x = grid1.columns.values  # amp values
                    y = grid1.index.values  # dur values
                    z = grid1.values-grid2.values  # result_0 values

                    x, y = np.meshgrid(x, y)

                self.data[combination] = [x, y, z]

        self.base_data = copy.deepcopy(self.data)

        if self.fft_mode:
            self.switch_mode(self.fft_mode)

    def recalculate(self,control_dict):
        for i,combination in enumerate(control_dict.keys()):
            # Dictionary with desired values
            keys = list(self.measurement_parameters.keys())
            desired_values = {keys[i]: combination[i] for i in range(len(combination))}

            # Filter for the parameters to match
            filtered_df = self.df.loc[(self.df[list(desired_values)] == pa.Series(desired_values)).all(axis=1)]

            if len(filtered_df) == 1:
                try:
                    self.apply_thresholds(filtered_df,control_dict[combination])
                except Exception as e:
                    print("ERROR when recalculating: ", e)

            self.progress_bar.setValue(int((i+1) / len(control_dict) * 100))

    def prepare_fit_dataframe(self,fit_parameters):
        values=np.array(self.active_combinations,dtype=object)
        placeholders=np.zeros((len(values),len(fit_parameters)))
        data=np.concatenate((values,placeholders),axis=1,dtype=object)
        self.fitted_params_df=pa.DataFrame(data,columns=self.parameter_map+fit_parameters)


    def get_offset(self,filtered_df):
        #check for all elements of df.trace==filtered_df.trace and return the index of the matching column
        trace=list(filtered_df.trace)[0]
        other_matches=self.df.loc[self.df.trace==trace]
        index_of_interest=list(filtered_df.index)[0]
        indexes=list(other_matches.index)
        offset=indexes.index(index_of_interest)
        return offset

    def apply_thresholds(self,filtered_df,thresholds):
        counts_all=np.array(list(filtered_df.Trace)[0])
        offset_index = self.get_offset(filtered_df)

        ssrs=[]
        for i in range(len(self.ana_seq)):
            ssrs.append(counts_all[i+int(offset_index*len(self.ana_seq))::int(self.simultaneous_measurements)*len(self.ana_seq)])

        msks=[]
        msks_neg=[]
        init_mask=np.full(len(ssrs[0]),True) #at first keep all values
        for i,ssr in enumerate(ssrs):
            if self.ana_seq[i][0] == "init":
                rule=thresholds[i]["combo_box"]
                num_index=f'num{["1","2"][rule=="<"]}_input'
                msk=eval(f'ssr {rule}= ({thresholds[i]["slider"]} {["+","-"][rule=="<"]} {thresholds[i][num_index]})')
                msks.append(msk)
                init_mask=init_mask & msk

        counter=0
        i_ssrs=[] #initialized ssrs
        for i,ssr in enumerate(ssrs):
            if self.ana_seq[i][0] == "result":
                i_ssr=ssr[init_mask]
                i_ssrs.append(i_ssr)

                rule = thresholds[i]["combo_box"]
                rule_neg = ["<", ">"][rule == "<"]  # switch rule

                num_index=f'num{["1", "2"][rule == "<"]}_input'
                msk = eval(
                    f'i_ssr {rule}= ({thresholds[i]["slider"]} {["+", "-"][rule == ">"]} {thresholds[i][num_index]})')

                num_index_neg=f'num{["1", "2"][rule_neg == "<"]}_input'
                msk_neg = eval(
                    f'i_ssr {rule_neg} {thresholds[i]["slider"]} {["+", "-"][rule_neg == ">"]} {thresholds[i][num_index_neg]}')

                if np.sum(msk)+np.sum(msk_neg)!=0:
                    value=np.sum(msk)/(np.sum(msk)+np.sum(msk_neg))
                else:
                    value=0

                self.df.at[list(filtered_df.index)[0],"recalculated_"+str(counter)]=value
                counter+=1



    def correspondences(self,label=None,combi=None):
        if label==None and combi==None:
            return
        elif label!=None:
            return self.label_to_combi[label]
        elif combi!=None:
            return self.combi_to_label[combi]

    # def generate_data(self):
    #     """
    #     Generate synthetic data.
    #     """
    #     self.two_d = False
    #     self.label_to_combi={}
    #     self.combi_to_label={}
    #
    #     for i in range(self.N_lines):
    #         param=("gaga", np.random.choice([" 0 ","par 2", "dd"]))
    #         label=str(param)
    #         self.label_to_combi[label]=param
    #         self.combi_to_label[param]=label
    #
    #         n=int(np.random.random()*100)
    #
    #         x = np.linspace(0, 10*n/100, n)
    #         y = 3 * np.sin(2 * x) + np.random.normal(0, 0.2, len(x))
    #         self.data[param]=(x,y,[])
    #
    #     self.base_data=copy.deepcopy(self.data)
    #     return self.data
    #
    # # Generate Dummy Data
    # def generate_2d_data(self,nx=50, ny=50, noise_level=1.0):
    #     """
    #     Generate dummy 2D data with a known surface function and added noise.
    #
    #     Parameters:
    #         nx (int): Number of points along the x-axis.
    #         ny (int): Number of points along the y-axis.
    #         noise_level (float): Standard deviation of the noise added to the data.
    #
    #     Returns:
    #         x, y, z (ndarray): Meshgrid arrays of x, y, and noisy surface z.
    #     """
    #     self.two_d=True
    #     self.label_to_combi={}
    #     self.combi_to_label={}
    #
    #     param = ("2d", np.random.choice([" 0 ","par 2", "dd"]))
    #
    #
    #     label = str(param)
    #     self.label_to_combi[label] = param
    #     self.combi_to_label[param] = label
    #
    #
    #     # Define x and y ranges
    #     x = np.linspace(-5, 5, nx)
    #     y = np.linspace(-5, 5, ny)
    #     x, y = np.meshgrid(x, y)
    #
    #     # Define a surface function
    #     z = 3 * x ** 2 + 2 * y ** 2 + 1.5 * x * y - 5 * x + 4 * y + 10
    #
    #     # Add Gaussian noise
    #     z_noisy = z + np.random.normal(0, noise_level, size=z.shape)
    #
    #     z_noisy[25,25]=np.nan
    #
    #     self.data[param]=[x,y,z_noisy]
    #     self.base_data=copy.deepcopy(self.data)
    #     return self.data

    def read_code(self,code_content):

        n_nuc_meas = self.extract_nuclear_measurements()#(code_content)
        ana_seq = self.extract_ana_seq(code_content)
        indexes = self.extract_step_idx(code_content)

        self.simultaneous_measurements = n_nuc_meas
        self.ana_seq = np.array(eval(ana_seq[ana_seq.index("=")+1:]),dtype=object)
        self.ana_seq = self.ana_seq[list(indexes.values())] #bring ana_seq into order
        self.indexes = indexes

    def extract_nuclear_measurements(self):
        trace=list(self.df.trace)[0]
        other_matches=self.df.loc[self.df.trace==trace]
        indexes=list(other_matches.index)
        return len(indexes)

    def extract_ana_seq(self, code_content):
        """Extract the entire ana_seq list, even if it spans multiple lines."""
        start_pattern = r"ana_seq\s*=\s*\["
        end_pattern = r"\]"
        start_match = re.search(start_pattern, code_content)

        if start_match:
            start_index = start_match.start()
            # Find the closing bracket that matches the list
            depth = 0
            for i in range(start_index, len(code_content)):
                if code_content[i] == "[":
                    depth += 1
                elif code_content[i] == "]":
                    depth -= 1
                    if depth == 0:
                        end_index = i
                        return f"ana_seq: {code_content[start_index:end_index + 1]}"
        return "ana_seq not found."

    def extract_step_idx(self, code_content):
        """
        Extract all occurrences of step_idx and their order of appearance.
        """
        matches = re.finditer(r"step_idx\s*=\s*(\d+)", code_content)
        result = {}
        for idx, match in enumerate(matches, start=1):
            result[idx]= int(match.group(1)) #idx is the order of appearance, match.group(1) is the extracted step index
        return result if result else "step_idx not found."


    def perform_fit(self,fit_name, parameter_combination, fit_manager,fit_app):
        """
        Perform fitting using a specified fit function.
        Save the results in `fit_results` and update `fit_parameters`.
        """
        try:
            if not self.data[parameter_combination]:
                raise ValueError("No data for parameter combination:", parameter_combination)
        except:
            raise ValueError("No data for parameter combination ", parameter_combination)

        x_data, y_data,z_data = self.data[parameter_combination]

        x_data,y_data,z_data=fit_app.run_code(x_data,y_data,z_data)

        fit_data = fit_manager.fits[fit_name]
        if not fit_data:
            raise ValueError(f"Fit function '{fit_name}' not found in FitManager.")

        expression = fit_data["machine_expression"]
        parameters = fit_data["parameters"][parameter_combination]

        # Define the fit function
        def fit_function(x, **kwargs):
            params_in_order=list(kwargs.values())
            return fit_data["function"](x,*params_in_order) #eval(expression, {"np": np}, {"x": x, **kwargs})

        def fit_function2d(x,y,**kwargs):
            params_in_order = list(kwargs.values()) #[kwargs[key] for key in fit_data["function"].param_order]
            return fit_data["function"](x,y,*params_in_order) #eval(expression, {"np": np}, {"x": x,"y":y, **kwargs})

        # Create lmfit Model
        if self.two_d:
            msk=~np.isnan(z_data)
            model = Model(fit_function2d, independent_vars=["x", "y"])
        else:
            msk=~np.isnan(y_data)
            model = Model(fit_function)


        # recall the previous data
        if fit_name not in self.fit_results.keys():
            self.fit_results[fit_name] = {
                "expression": expression,
                "parameters": {},
                "result": {},
                "best_fit": {},
            }

        try:
            if self.two_d: #if 2d plot
                params = Parameters()
                for param in parameters:
                    params.add(
                        param,
                        value=parameters[param]["initial_guess"],
                        vary=parameters[param]["vary"]
                    )

                result = model.fit(z_data, params, x=x_data, y=y_data,nan_policy="omit")
                # Update the fit parameters with the results
                for param in parameters:
                    parameters[param]["fitted_value"] = result.params[param].value
                    parameters[param]["std"] = result.params[param].stderr

                #self.fit_parameters[name][parameter_combination] = copy.deepcopy(self.fits[name]["parameters_blueprint"])

                # Save the updated parameters and the expression
                self.fit_results[fit_name]["parameters"][parameter_combination]={param: copy.deepcopy(data) for param, data in parameters.items()}
                self.fit_results[fit_name]["result"][parameter_combination] = result
                self.fit_results[fit_name]["best_fit"][parameter_combination] = fit_function2d(x_data,y_data,**result.best_values)

            else:
                params = Parameters()
                for param in parameters:
                    params.add(
                        param,
                        value=parameters[param]["initial_guess"],
                        vary=parameters[param]["vary"]
                    )

                result = model.fit(y_data, params, x=x_data)#,nan_policy="omit") #or propagate

                # Update the fit parameters with the results
                for param in parameters:
                    parameters[param]["fitted_value"] = result.params[param].value
                    parameters[param]["std"] = result.params[param].stderr


                # Save the updated parameters and the expression
                self.fit_results[fit_name]["parameters"][parameter_combination]={param: copy.deepcopy(data) for param, data in parameters.items()}
                self.fit_results[fit_name]["result"][parameter_combination] = result
                self.fit_results[fit_name]["best_fit"][parameter_combination] = fit_function(x_data,**result.best_values)

            # update the fitted_params_df
            desired_values={self.parameter_map[i]:parameter_combination[i] for i in range(len(parameter_combination))}
            new_values={param: data["fitted_value"] for param, data in parameters.items()}

            # Match rows where the conditions are met
            mask = (self.fitted_params_df[list(desired_values)] == pa.Series(desired_values)).all(axis=1)

            # Update the specified rows and columns
            for col, val in new_values.items():
                self.fitted_params_df.loc[mask, col] = val

            return True  # Fit succeeded
        except Exception as e:
           print(f"Fit error for '{fit_name}': {e}")
           return False  # Fit failed

    def get_fit_results(self, fit_name):
        """
        Retrieve fit results for a given fit function.
        """
        return self.fit_results.get(fit_name, None)

    def switch_mode(self,state):
        self.fft_mode=state
        for combination in self.data.keys():
            if state==2:#FFT mode

                x,y,z=self.data[combination]


                if self.two_d:
                    # Compute the 2D real FFT
                    z_fft = abs(np.fft.rfft2(z)[:(len(z)//2+1)])

                    # Calculate the frequencies for both X and Y axes
                    x_fft = np.fft.rfftfreq(x.shape[1], (x[0][1]-x[0][0]))
                    y_fft = np.fft.rfftfreq(y.shape[0], (y[1][0]-y[0][0]))

                    x_fft,y_fft=np.meshgrid(x_fft,y_fft)


                else:
                    z_fft=[]
                    y_fft = np.fft.rfft(y)

                    # Calculate the frequency axis
                    x_fft = np.fft.rfftfreq(len(x), (x[1] - x[0]))

                self.data[combination]=[abs(x_fft),abs(y_fft),z_fft]
            else:
                #revert to original data
                self.data=copy.deepcopy(self.base_data)

    def number_of_lines(self):
        return len(self.data)

class FitApp(QMainWindow):
    def __init__(self,root_path=""):
        super().__init__()
        self.history_manager=SQLiteHistoryManager()
        self.history_index=self.history_manager.get_count()
        self.previous_tab_index = 0
        self.colorbars={}
        self.mouse_x,self.mouse_y=0,0
        self.show_uncertainity=True

        # self.combi_idx_x=0 # the combi index for parameter giving the subplots x axis
        # self.combi_idx_y=0 # the combi index for parameter giving the subplots y axis
        self.paramx={}#"__None__"
        self.paramy={}#"__None__"

        self.plot_layouts = {}

        self.tab_states = {}  # Dictionary to store the state of each tab

        self.label_ncols=2
        self.label_frontsize=10

        self.setWindowTitle("Postprocess v1.0")
        self.setGeometry(100, 100, 1200, 800)

        self.fit_manager = FitManager()
        self._setup_default_fit_functions()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QHBoxLayout(self.central_widget)

        # Splitter for shared controls and tabs
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        # Shared fitting controls
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.splitter.addWidget(self.left_panel)

        self.fit_button = QPushButton("Fit")
        self.fit_button.clicked.connect(self.perform_fit)
        self.left_layout.addWidget(self.fit_button)

        self.fit_literal_input = QLineEdit()
        self.fit_literal_input.setPlaceholderText("Enter fit function literal...")
        self.fit_literal_input.textChanged.connect(self.on_literal_change)
        self.left_layout.addWidget(self.fit_literal_input)

        self.fit_combobox = QComboBox()
        self.fit_combobox.addItems(self.fit_manager.list_display_names())
        self.fit_combobox.currentTextChanged.connect(self.on_fit_selection_changed)
        self.left_layout.addWidget(self.fit_combobox)

        self.stacked_widget = QStackedWidget()
        self.left_layout.addWidget(self.stacked_widget)

        self.parameter_table = EnhancedTable()

        self.parameter_table.setColumnCount(5)
        self.parameter_table.setRowCount(0)
        self.parameter_table.setHorizontalHeaderLabels(["Parameter", "Initial Guess", "Fitted Value", "Vary","Set initial guess"])
        self.parameter_table.itemChanged.connect(self.on_table_item_changed)
        self.stacked_widget.addWidget(self.parameter_table)

        self.easy_parameter_table = QTableWidget(0, 0)
        #self.easy_parameter_table.setHorizontalHeaderLabels(["Combi", "Initial Guess", "Fitted Value", "Vary","Set initial guess"])
        self.stacked_widget.addWidget(self.easy_parameter_table)

        Hbox=QWidget()
        Hbox_layout=QHBoxLayout(Hbox)

        self.FFT_mode_checkbox = QCheckBox()
        self.FFT_mode_checkbox.setChecked(False)
        self.FFT_mode_checkbox.setText("FFT mode")
        self.FFT_mode_checkbox.stateChanged.connect(self.switch_mode)

        self.guess=QPushButton("Guess")
        self.guess.clicked.connect(self.guess_initial_values)

        Hbox_layout.addWidget(self.FFT_mode_checkbox)
        Hbox_layout.addWidget(self.guess)

        self.left_layout.addWidget(Hbox)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #000;
                        border-radius: 5px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #05B8CC;
                        width: 10px;
                    }
                """)

        #####added
        self.root_path=root_path
        self.root_path_button = QPushButton(f"{root_path}")
        self.root_path_button.setMinimumSize(50,30)
        self.root_path_button.clicked.connect(self.select_directory)
        self.left_layout.addWidget(self.root_path_button)

        # Setup TreeView
        self.tree_view = QTreeView()

        if root_path=="":
            self.select_directory()
        else:
            # Setup custom file model
            self.model = NonLazyFileModel(root_path, self.progress_bar)
            self.tree_view.setModel(self.model)

        self.tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree_view.setHeaderHidden(False)

        # Connect selection change signal
        self.tree_view.selectionModel().selectionChanged.connect(self.on_item_selected)

        # Setup search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.textChanged.connect(self.on_search_changed)

        # Setup "Add to Selection" button
        self.add_button = QPushButton("Add to Selection/Reload")
        self.add_button.clicked.connect(self.add_to_selection)


        # Add widgets to layout
        self.left_layout.addWidget(self.search_input)
        self.left_layout.addWidget(self.tree_view)
        self.left_layout.addWidget(self.add_button)
        self.left_layout.addWidget(self.progress_bar)

        ####added
        # Tab widget for plots
        self.tab_widget = TabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.tabRemovedSignal.connect(self.on_tab_removed)
        self.splitter.addWidget(self.tab_widget)

        self.data_processors = {}
        self.plot_layouts={} #will contain the subplots dimentions
        self.indexes = {}
        self.tabs_with_plot={}
        self.Tables={}
        self.average_over_list_widgets={}
        self.setters={}
        self.z_axis_list_widgets={}
        self.x_axis_list_widgets={}
        self.y_axis_list_widgets={}
        self.stacked_widgets={}
        self.apply_code_checkboxes = {}
        self.code_inputs = {}
        self.highliners={} # we have to keep them alive,
        #for tab_name in ["Tab 1"]:
        #    self.add_tab(tab_name)


        # Set up the initial expression display
        self.on_fit_selection_changed(self.fit_combobox.currentText())

    def on_tab_removed(self,index):
        #clean up all the memory of what was related to that tab
        name = self.tab_widget.tabText(index)
        for dictionary in [self.data_processors,self.tabs_with_plot,self.paramx,self.paramy,self.plot_layouts,self.indexes,self.highliners,self.Tables,self.average_over_list_widgets,
                           self.z_axis_list_widgets,self.x_axis_list_widgets,self.y_axis_list_widgets,self.apply_code_checkboxes,self.code_inputs,self.stacked_widgets,self.fit_manager.fits,
                           self.fit_manager.functions,self.fit_manager.fit_parameters,self.tab_states,self.setters]:
        
            if name in dictionary.keys():
                del dictionary[name]


    def on_item_selected(self, selected, deselected):
        """
        Called when an item in the tree view is selected.
        Opens an image if a picture file is selected.
        """
        selected_indexes = selected.indexes()
        if selected_indexes:
            selected_index = selected_indexes[0]
            item = self.model.itemFromIndex(selected_index)
            full_path = item.data(Qt.UserRole)  # Full path of the file or folder

            # Check if the selected file is an image
            if full_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                self.show_image(full_path)

    def show_image(self, image_path):
        """
        Opens a new window displaying the selected image.
        """
        self.image_window = QWidget()
        self.image_window.setWindowTitle("Image Viewer")
        self.image_window.setGeometry(400, 200, 600, 600)

        layout = QVBoxLayout()
        label = QLabel()
        pixmap = QPixmap(image_path)

        label.setPixmap(pixmap.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        layout.addWidget(label)
        self.image_window.setLayout(layout)
        self.image_window.show()

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select root directory",
            self.root_path
        )

        if directory:
            self.model = NonLazyFileModel(directory,self.progress_bar)

            # Setup TreeView
            self.tree_view.setModel(self.model)
            self.root_path_button.setText(f"{directory}")
            fi = open("root_folder.txt", "w")
            fi.writelines([directory])
            fi.close()

    def on_search_changed(self, text):
        """
        Filter the tree view based on the search term and expand matching items.
        """
        search_str = text.strip().lower()

        def recursive_filter_and_expand(parent_item, parent_index):
            visible = False
            for row in range(parent_item.rowCount()):
                child_item = parent_item.child(row)
                item_text = child_item.text().lower()
                child_index = self.model.indexFromItem(child_item)

                # Recursively filter children
                child_visible = recursive_filter_and_expand(child_item, child_index)

                # Match current item or any visible children
                is_visible = search_str in item_text or child_visible
                self.tree_view.setRowHidden(row, parent_index, not is_visible)

                # Expand tree if current item or its children match
                if is_visible:
                    self.tree_view.expand(parent_index)

                # Update visibility for parent
                visible = visible or is_visible
            return visible

        root_item = self.model.invisibleRootItem()
        root_index = self.tree_view.rootIndex()
        recursive_filter_and_expand(root_item, root_index)

    def guess_initial_values(self):
        processor=self.data_processors[self.current_tab_name]["processor"]

        selected_fit = next(
            (name for name, data in self.fit_manager.fits.items() if
             data["display_name"] == self.fit_combobox.currentText()),
            None
        )

        data=self.fit_manager.fits[selected_fit]
        if len(data.keys()):
            params=data["parameters"][list(data["parameters"].keys())[0]]
            param_names=list(params.keys())

            if processor.two_d==False:
                for combi in processor.data.keys():
                    x,y,z=processor.data[combi]
                    guesses=self.fit_manager.get_smat_initial_guesses(selected_fit,x,y,param_names)
                    for par,value in guesses.items():
                        data["parameters"][combi][par]["initial_guess"]=float(value)

                self.update_parameter_table(self.fit_manager.fits[selected_fit]["parameters"])
            else:
                print("initial guessing not available for 2d")




    def add_to_selection(self):
        """
        Handle the "Add to Selection" button click.
        Prints the path and file/folder name of the selected item.
        """
        selected_indexes = self.tree_view.selectionModel().selectedIndexes()
        if selected_indexes:
            if len(selected_indexes)==1:
                selected_index = selected_indexes[0]
                item = self.model.itemFromIndex(selected_index)
                full_path = item.data(Qt.UserRole)  # Full path of the file or folder
                name = item.text()  # Name of the file or folder
                if name in self.data_processors.keys():
                    processor=self.data_processors[name]["processor"]
                    processor.load_data()

                    #yeah, this should be in a function, but I am too lazy right now, it is areplication of what is written in init plot ui
                    table=self.Tables[name]
                    max_rows = max(len(processor.measurement_parameters[key]) for key in processor.measurement_parameters)
                    table.setRowCount(max_rows)

                    # Populate the table
                    for col, keys in enumerate(processor.measurement_parameters):
                        if keys=="__None__":
                            table.setColumnHidden(col,True)
                        for row, value in enumerate(processor.measurement_parameters[keys]):
                            table.setItem(row, col, QTableWidgetItem(str(value)))

                    # Select all cells at the start
                    self.select_all_cells(table)

                self.add_tab(name,full_path)
                self.switch_to_tab(name)
                




            else:
                names=[]
                pathes=[]
                for i in range(len(selected_indexes)):
                    selected_index = selected_indexes[i]
                    item = self.model.itemFromIndex(selected_index)
                    full_path = item.data(Qt.UserRole)  # Full path of the file or folder
                    name = item.text()  # Name of the file or folder
                    names.append(name)
                    pathes.append(full_path)

                name="+".join(names)
                try:
                    if name in self.data_processors.keys():
                        processor=self.data_processors[name]["processor"]
                        processor.load_data()

                        #yeah, this should be in a function, but I am too lazy right now, it is areplication of what is written in init plot ui
                        table=self.Tables[name]
                        max_rows = max(len(processor.measurement_parameters[key]) for key in processor.measurement_parameters)
                        table.setRowCount(max_rows)

                        # Populate the table
                        for col, keys in enumerate(processor.measurement_parameters):
                            if keys=="__None__":
                                table.setColumnHidden(col,True)
                            for row, value in enumerate(processor.measurement_parameters[keys]):
                                table.setItem(row, col, QTableWidgetItem(str(value)))

                    # Select all cells at the start
                    self.select_all_cells(table)
                except:
                    print(f"could not reload data for {name}")
                self.add_tab(name,pathes)
                self.switch_to_tab(name)
        else:
            print("No item selected.")

    def switch_mode(self,state):

        for processor_name in self.data_processors.keys():
            processor=self.data_processors[processor_name]["processor"]
            processor.switch_mode(state)
            self.clear_plot(processor_name)

        self.plot_all_tabs()

    def _setup_default_fit_functions(self):
        pass

    def switch_to_tab(self,name):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == name:
                self.tab_widget.setCurrentIndex(i)  # Switch to existing tab if it already exists
                return 1
        return 0

    def add_code_tab(self, sub_tabs, folder_path,tab_name):
        """
        Create the Code sub-tab and add it to the given sub-tabs widget.
        """
        code_tab = QWidget()
        code_layout = QVBoxLayout(code_tab)

        processor=self.data_processors[tab_name]["processor"]

        # Python editor with syntax highlighting
        code_editor = QPlainTextEdit()
        code_editor.setFont(QFont("Courier New", 12))
        code_editor.setReadOnly(True)
        highlighter = PythonSyntaxHighlighter(code_editor.document())

        # Load meas_code.py content
        code_file = os.path.join(folder_path, "meas_code.py")
        extracted_info = []

        if os.path.isfile(code_file):
            with open(code_file, "r") as file:
                code_content = file.read()
            code_editor.setPlainText(code_content)
            code_editor.update()

            processor.read_code(code_content)

        else:
            code_editor.setPlainText("meas_code.py not found in the folder.")

        # Add components to the layout
        code_layout.addWidget(code_editor)
        sub_tabs.addTab(code_tab, "Code")

    def add_sequence_tab(self, sub_tabs, folder_path):
        """
        Create the Sequence sub-tab and add it to the given sub-tabs widget.
        """
        sequence_tab = QWidget()
        sequence_layout = QVBoxLayout(sequence_tab)

        sequence_editor = QTextEdit()
        sequence_editor.setReadOnly(True)

        # Load awg-file.txt content
        sequence_file = os.path.join(folder_path, "awg-file.txt")
        if os.path.isfile(sequence_file):
            with open(sequence_file, "r") as file:
                sequence_content = file.read()
            sequence_editor.setPlainText(sequence_content)
        else:
            sequence_editor.setPlainText("awg-file.txt not found in the folder.")

        sequence_layout.addWidget(sequence_editor)
        sub_tabs.addTab(sequence_tab, "Sequence")



    def show_error(self, message):
        """
        Display an error message in a popup or status bar.
        """
        print(f"Error: {message}")  # Placeholder for actual error handling

    def add_tab(self, name,folder=r"/home/pierre/Dokumente/Uni/20241216-h21m51s55_Nuc_SSR_electron_rabi_or_ODMR"):

        if self.switch_to_tab(name):
            return

        self.paramx[name] = "__None__"
        self.paramy[name] = "__None__"

        overtab=QTabWidget()
        tab = QWidget()
        processor=DataProcessor(folder,self.progress_bar)

        self.plot_layouts[name]=(1,1)
        self.indexes[name] = {"paramx": {par: i for i, par in enumerate(processor.measurement_parameters["__None__"])},
                              "paramy": {par: i for i, par in enumerate(processor.measurement_parameters["__None__"])}}
        figure,ax,canvas=self.init_plot_space(name,tab,processor)

        # if "2d" in name:
        #     processor.generate_2d_data()
        # else:
        #     processor.generate_data()

        self.data_processors[name] = {
            "processor": processor,
            "canvas": canvas,
            "figure": figure,
            "axes": np.array(ax)
        }


        self.tab_widget.addTab(overtab, name)
        overtab.addTab(tab,name)
        if type(folder)!=type([]):
            self.add_code_tab(overtab,folder,name)
            self.add_sequence_tab(overtab,folder)
        else:
            self.add_code_tab(overtab,folder[0],name)
            self.add_sequence_tab(overtab,folder[0])

        self.plot_data_single(name)

        self.splitter.setStretchFactor(0,9)
        self.splitter.setStretchFactor(1, 9)

    def get_tab_widget_by_name(self,parent, tab_name):
        # Loop through tabs and match the name
        for index in range(parent.count()):
            if parent.tabText(index) == tab_name:
                return parent.widget(index)
        return None  # Return None if no matching tab is found


    def update_plot_area_and_plot(self,tab_name=None):
        if tab_name==None:
            tab_name=self.current_tab_name

        tab=self.get_tab_widget_by_name(self.tab_widget,tab_name)
        figure,ax,canvas=self.init_plot_space(tab_name,tab)

        self.data_processors[tab_name].update({
            "canvas": canvas,
            "figure": figure,
            "axes": np.array(ax)
        })
        self.plot_data_single(tab_name)

    def select_all_cells(self,table):
        """Select all non-empty cells in the table."""
        for col in range(table.columnCount()):
            for row in range(table.rowCount()):
                item = table.item(row, col)
                if item and item.text():
                    item.setSelected(True)

    def handle_selection_change(self):

        table = self.Tables[self.current_tab_name]

        processor = self.data_processors[self.current_tab_name]["processor"]
        datatypes = processor.df._Datatypes

        selected_values = {list(processor.measurement_parameters.keys())[col]: [] for col in range(table.columnCount())}

        for item in table.selectedItems():
            if item.text():
                col = item.column()
                col_name = list(processor.measurement_parameters.keys())[col]
                selected_values[col_name].append(datatypes[col_name].type(item.text()))

        for col in range(table.columnCount()):
            col_name = list(processor.measurement_parameters.keys())[col]
            if not selected_values[col_name]:
                for row in range(table.rowCount()):
                    item = table.item(row, col)
                    if item and item.text():
                        item.setSelected(True)
                        selected_values[col_name].append(datatypes[col_name].type(item.text()))

        # Get the unselected cells
        unselected_values = {list(processor.measurement_parameters.keys())[col]: [] for col in
                             range(table.columnCount())}
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                col_name = list(processor.measurement_parameters.keys())[col]
                item = table.item(row, col)
                if item and item.text() and not item.isSelected():
                    unselected_values[col_name].append(datatypes[col_name].type(item.text()))

        # Deselect empty cells immediately
        for item in table.selectedItems():
            if not item.text():
                item.setSelected(False)

        # remove unwanted columns
        reserved_variables=[processor.x_axis_param, processor.y_axis_param, processor.z_axis_param,
                         processor.difference_param, *processor.average_params]

        update=True
        for reserved in reserved_variables:
            try:
                if reserved not in [*processor.measurement_parameters,*processor.measurement_observations]:
                    update=False

                if reserved!="__None__":
                    selected_values.pop(reserved)

            except Exception as e:
                print(f"Impossible to remove parameter {reserved} from selected_values:\n", e)

        if update:
            active_combinations,parameter_map = self.compute_ordered_combinations(selected_values)
            processor.active_combinations = active_combinations
            processor.unselected = unselected_values
            processor.parameter_map = parameter_map
        else:
            # check if the user forgot to select a valid x axis.
            for reserved in reserved_variables:
                if (reserved in [*processor.measurement_parameters,*processor.measurement_observations]) and reserved not in processor.parameter_map:
                    print("Please use a correct plot axis. Correct plot axis are",processor.parameter_map, "and the fit pareters")
                    return 0

        return 1
        # if processor.parameter_map:
        #     paramx = processor.parameter_map[self.combi_idx_x]
        #     paramy = processor.parameter_map[self.combi_idx_y]
        #     map=True
        # else:
        #     map=False

        # if map:
        #     self.combi_idx_x = processor.parameter_map.index(paramx)
        #     self.combi_idx_y = processor.parameter_map.index(paramy)

    def compute_ordered_combinations(self, selected_values, generate_all=False):
        """Compute ordered combinations and optionally generate all possible combinations."""

        parameter_map=list(selected_values.keys())

        if generate_all:
            # Generate all combinations for the DataFrame creation
            raw_combinations = list(product(*[values for values in selected_values.values()]))
        else:
            # Generate combinations based on current selection
            raw_combinations = list(product(
                *[[(col, value) for value in values] for col, values in selected_values.items()]))

        if generate_all:
            return [tuple(combination) for combination in raw_combinations]

        ordered_combinations = []
        for combination in raw_combinations:
            # Convert combination to a tuple
            ordered_combinations.append(tuple(value for _, value in combination))
        return ordered_combinations,parameter_map

    def add_to_history(self,code):
        if os.path.isfile("code_history.txt"):
            fi = open("code_history.txt", "r")
            self.lines = fi.readlines()
            fi.close()
            for line in self.lines:
                arguments = line[:-1].split("|")
                self.add_fit_function(*arguments)

    def run_code(self,x,y,z,local_scope=None,tab_name=None):
        if tab_name==None:
            tab_name=self.current_tab_name

        if self.apply_code_checkboxes[tab_name].isChecked():
            # Get user code
            user_code = self.code_inputs[self.current_tab_name].toPlainText()

            self.history_manager.add_input(user_code)

            if local_scope==None:
                # Get the local scope snapshot
                local_scope = locals()

            # Initialize x and y in the local scope
            local_scope["x"] = x
            local_scope["y"] = y
            local_scope["z"] = z

            try:
                # Execute the user code using the local scope
                exec(user_code, globals(), local_scope)

                # Update self.x and self.y with the potentially modified values
                x = local_scope.get("x", x)
                y = local_scope.get("y", y)
                z = local_scope.get("z", z)

            except Exception as e:
                # Show error message
                print( "Error", f"An error occurred:\n{e}")

        return x,y,z

    def export_data(self):

        folder_path, _ = QFileDialog.getSaveFileName(
            None, "Select or Create Folder", "", "Folder Name (*)"
        )

        if folder_path:  # If a folder path was provided
            # Ensure the path ends with a folder separator
            folder_path = os.path.dirname(folder_path) if os.path.isfile(folder_path) else folder_path

            # Create the folder if it doesn't exist
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Folder created: {folder_path}")

            processor=self.data_processors[self.current_tab_name]["processor"]
            data=processor.data

            try:
                # Save the DataFrame to an HDF5 file
                with pa.HDFStore(os.path.join(folder_path,'data_revisited.hdf')) as store:
                    store.put('/df', processor.df, format='table')  # Using table format for appendable storage
            except:
                print("unable to save hdf file")

            try:
                # Save to a CSV file
                with open(os.path.join(folder_path,"x_y_z_data.csv"), "w", newline="") as file:
                    writer = csv.writer(file)
                    # Write a header
                    writer.writerow(["combi", "x", "y", "z"])
                    # Write the data
                    for combi, (x, y, z) in data.items():
                        writer.writerow([combi, x, y, z])

                # just because I feel this is going to be useful:
                # # Load from the CSV file
                # with open("data.csv", "r") as file:
                #     reader = csv.DictReader(file)
                #     loaded_data = {
                #         eval(row["combi"]): (eval(row["x"]), eval(row["y"]), eval(row["z"]))
                #         for row in reader
                #    }

            except:
                print("unable to save x,y,z data")

            if self.current_tab_name in self.setters:
                try:
                    setter=self.setters[self.current_tab_name]
                    with open(os.path.join(folder_path, "thresholds.csv"), "w", newline="") as file:
                        writer = csv.writer(file)
                        # Write a header
                        writer.writerow(["combi", *(["slider","rule","exclude1","exclude2"]*len(processor.ana_seq))])
                        # Write the data
                        for combi in setter.control_dict.keys():
                            values=[]
                            for i in setter.control_dict[combi].keys():
                                values.extend(list(setter.control_dict[combi][i].values()))

                            writer.writerow([combi, *values])

                    # just because I feel this is going to be useful:
                    # # Load from the CSV file
                    # with open("data.csv", "r") as file:
                    #     reader = csv.DictReader(file)
                    #     loaded_data = {
                    #         eval(row["combi"]): (eval(row["x"]), eval(row["y"]), eval(row["z"]))
                    #         for row in reader
                    #    }

                except:
                    print("unable to save thresholds")

            # Retrieve selected fit from FitManager
            selected_fit = next(
                (name for name, data in self.fit_manager.fits.items() if data["display_name"] == self.fit_combobox.currentText()),
                None
            )
            nested_data = {"expression":self.fit_manager.fits[selected_fit]["expression"]}

            for i,combi in enumerate(self.fit_manager.fits[selected_fit]["parameters"].keys()):
                params={key:str(value) for key,value in zip(processor.parameter_map,combi)}
                fit_parameters=self.fit_manager.fits[selected_fit]["parameters"][combi]
                nested_data[f"Params_{i}"]=params
                nested_data[f"fit_parameters_{i}"]=fit_parameters

            with open(os.path.join(folder_path,"parameters.json"), "w") as fi:
                json.dump(nested_data, fi, indent=4)

            self.data_processors[self.current_tab_name]["figure"].savefig(os.path.join(folder_path,"plot.png"))

        else:
            print("No folder selected.")



    def create_plot_UI(self,name,tab,processor):
        layout = QHBoxLayout(tab)
        Layout = QSplitter(Qt.Horizontal)
        layout.addWidget(Layout)

        plot_and_table = QWidget()
        Layout.addWidget(plot_and_table)

        Sub_layout = QVBoxLayout(plot_and_table)
        sub_layout = QSplitter(Qt.Vertical)
        Sub_layout.addWidget(sub_layout)

        table = QTableWidget()
        sub_layout.addWidget(table)

        ####Take care of the parameter table
        table.setColumnCount(len(processor.measurement_parameters.keys()))
        table.setHorizontalHeaderLabels(list(processor.measurement_parameters.keys()))

        # Set selection mode and behavior
        table.setSelectionMode(QTableWidget.MultiSelection)
        table.setSelectionBehavior(QTableWidget.SelectItems)

        # Determine the maximum number of rows needed
        max_rows = max(len(processor.measurement_parameters[key]) for key in processor.measurement_parameters)
        table.setRowCount(max_rows)

        # Populate the table
        for col, keys in enumerate(processor.measurement_parameters):
            if keys=="__None__":
                table.setColumnHidden(col,True)
            for row, value in enumerate(processor.measurement_parameters[keys]):
                table.setItem(row, col, QTableWidgetItem(str(value)))


        # Select all cells at the start
        self.select_all_cells(table)

        # Connect selection changes
        table.itemSelectionChanged.connect(self.handle_selection_change)

        #### Take care of the plot controls
        plot_controls = QWidget()
        plot_controls_layout = QVBoxLayout(plot_controls)

        separator = QSplitter(Qt.Vertical)
        plot_controls_layout.addWidget(separator)

        container_up = QWidget()
        container_down = QWidget()

        container_up_layout = QVBoxLayout(container_up)
        container_down_layout = QVBoxLayout(container_down)

        separator.addWidget(container_up)
        separator.addWidget(container_down)

        container_down_layout.setSpacing(1)

        plot_axes_control_area = QWidget()
        plot_axes_control_layout = QGridLayout(plot_axes_control_area)
        container_up_layout.addWidget(plot_axes_control_area)

        y_axis_list = QListWidget()
        average = QListWidget()
        x_axis_list = QListWidget()
        z_axis_list = QListWidget()

        y_axis_list.addItems(list(processor.measurement_observations.keys()))
        y_axis_list.addItems(list(processor.measurement_parameters.keys()))
        average.addItems(list(processor.measurement_parameters.keys()))
        x_axis_list.addItems(list(processor.measurement_parameters.keys()))
        z_axis_list.addItems(list(processor.measurement_observations.keys()))

        y_axis_list.itemClicked.connect(self.on_y_axis_param_changed)
        average.itemClicked.connect(self.on_average_param_changed)
        x_axis_list.itemClicked.connect(self.on_x_axis_param_changed)
        z_axis_list.itemClicked.connect(self.on_z_axis_param_changed)

        average.setSelectionMode(QListWidget.MultiSelection)

        plot_axes_control_layout.addWidget(QLabel("y axis"), 0, 0)
        plot_axes_control_layout.addWidget(y_axis_list, 1, 0)
        plot_axes_control_layout.addWidget(QLabel("average over axis"), 0, 1)
        plot_axes_control_layout.addWidget(average, 1, 1)
        plot_axes_control_layout.addWidget(QLabel("x axis"), 2, 0)
        plot_axes_control_layout.addWidget(x_axis_list, 3, 0)
        plot_axes_control_layout.addWidget(QLabel("z axis (optional)"), 2, 1)
        plot_axes_control_layout.addWidget(z_axis_list, 3, 1)


        container_up_layout.addWidget(QLabel("Column parameter:"))
        subplot_y_combobox = QComboBox()
        subplot_y_combobox.addItems(["__None__"] + list(processor.measurement_parameters.keys()))
        subplot_y_combobox.currentTextChanged.connect(self.on_subplot_y_combobox_changed)
        container_up_layout.addWidget(subplot_y_combobox)

        container_up_layout.addWidget(QLabel("Row parameter:"))
        subplot_x_combobox = QComboBox()
        subplot_x_combobox.addItems(["__None__"] + list(processor.measurement_parameters.keys()))
        subplot_x_combobox.currentTextChanged.connect(self.on_subplot_x_combobox_changed)
        container_up_layout.addWidget(subplot_x_combobox)

        container_up_layout.addWidget(QLabel("Subtract parameter:"))
        difference_combobox = QComboBox()
        difference_combobox.addItems(["__None__"] + list(processor.measurement_parameters.keys()))
        difference_combobox.currentTextChanged.connect(self.on_difference_combobox_changed)
        container_up_layout.addWidget(difference_combobox)

        plot_now_button = QPushButton("Plot now!")
        container_up_layout.addWidget(plot_now_button)
        plot_now_button.clicked.connect(self.plot_new_plot)

        apply_code_checkbox = QCheckBox("apply code")
        container_up_layout.addWidget(apply_code_checkbox)
        #apply_code_checkbox.stateChanged.connect(self.apply_code)

        # Text editor for Python code
        code_input = QPlainTextEdit()
        #code_input.setFont(QFont("Courier New", 12))
        self.highliners[name]=PythonSyntaxHighlighter(code_input.document())
        code_input.textChanged.connect(lambda :code_input.update())

        content=self.history_manager.get_element_by_index(self.history_index)

        code_input.setPlainText(content if content else "# You can apply code to x, y and z here before it is plotted or fitted\n#(In principle you have access to all app parameters here)\nx=x**2")
            #"# You can apply code to x, y and z here before it is plotted or fitted\n#(In principle you have access to all app parameters here)\nx=x**2")
        code_input.update()

        container_down_layout.addWidget(code_input)

        history_control_buttons=QWidget()
        history_layout=QHBoxLayout(history_control_buttons)

        forward_button = QPushButton()
        style = app.style()
        arrow_icon = style.standardIcon(style.SP_ArrowRight)
        forward_button.setIcon(arrow_icon)

        backwards_button = QPushButton()
        arrow_icon = style.standardIcon(style.SP_ArrowLeft)
        backwards_button.setIcon(arrow_icon)

        forward_button.clicked.connect(self.history_forward)
        backwards_button.clicked.connect(self.history_backward)

        history_layout.addWidget(backwards_button)
        history_layout.addWidget(forward_button)


        container_down_layout.addWidget(history_control_buttons)


        thresholds_button = QPushButton("Set thresholds")
        container_down_layout.addWidget(thresholds_button)
        thresholds_button.clicked.connect(self.open_measurements_viewer)

        export_button = QPushButton("Export data")
        export_button.clicked.connect(self.export_data)
        container_down_layout.addWidget(export_button)

        Layout.addWidget(plot_controls)
        Layout.setStretchFactor(0, 9)
        Layout.setStretchFactor(1, 1)

        self.Tables[name] = table
        self.average_over_list_widgets[name]=average
        self.z_axis_list_widgets[name] = z_axis_list
        self.x_axis_list_widgets[name] = x_axis_list
        self.y_axis_list_widgets[name] = y_axis_list
        self.apply_code_checkboxes[name]=apply_code_checkbox
        self.code_inputs[name]=code_input

        stacked_widget = QStackedWidget()
        sub_layout.addWidget(stacked_widget)

        self.stacked_widgets[name]=stacked_widget

        self.create_plot_space(name,stacked_widget)

    def history_forward(self):
        if self.history_index<self.history_manager.get_count():
            self.history_index=self.history_index+1
        res=self.set_history_code_text()

    def history_backward(self):
        if self.history_index>0:
            self.history_index=self.history_index-1
        res=self.set_history_code_text()

    def set_history_code_text(self):
        code_input=self.code_inputs[self.current_tab_name]
        content=self.history_manager.get_element_by_index(self.history_index)
        code_input.setPlainText(
            content if content else "# You can apply code to x, y and z here before it is plotted or fitted\n#(In principle you have access to all app parameters here)\nx=x**2")
        code_input.update()
        return content!=""

    def create_plot_space(self,name,sub_layout):

        self.tabs_with_plot[name]={}

        #1d
        TAB = QWidget()
        sub_layout.addWidget(TAB)
        self.tabs_with_plot[name][False] = TAB

        #2d
        tab_widget = QTabWidget()
        sub_layout.addWidget(tab_widget)

        # Sub-tabs
        original_tab = QWidget()
        fitted_tab = QWidget()
        diff_tab = QWidget()

        tab_widget.addTab(original_tab, "Original Data")
        tab_widget.addTab(fitted_tab, "Fitted Data")
        tab_widget.addTab(diff_tab, "Difference")

        tabs = [original_tab, fitted_tab, diff_tab]
        self.tabs_with_plot[name][True] = tabs

    def plot_new_plot(self):
        valid=self.handle_selection_change()
        if not valid:
            return
        self.on_subplot_x_combobox_changed(self.paramx[self.current_tab_name]) #update the plot axes
        self.on_subplot_y_combobox_changed(self.paramy[self.current_tab_name])  # update the plot axes
        self.data_processors[self.current_tab_name]["processor"].extract_data()

        nx, ny = self.plot_layouts[self.current_tab_name]
        if nx == 1:
            #self.combi_idx_x = self.data_processors[self.current_tab_name]["processor"].parameter_map.index("__None__")
            self.paramx[self.current_tab_name] = "__None__"
        if ny == 1:
            #self.combi_idx_y = self.data_processors[self.current_tab_name]["processor"].parameter_map.index("__None__")
            self.paramy[self.current_tab_name] = "__None__"

        self.update_plot_area_and_plot(self.current_tab_name)

        self.fit_manager.prepare_parameters(self.data_processors[self.current_tab_name]["processor"].data.keys())
        fit_name = self.fit_combobox.currentText()
        fit_data = self.fit_manager.fits[fit_name]
        self.update_parameter_table(fit_data["parameters"])



    def init_plot_space(self,name,tab=None,processor=None):
        # nx,ny=1,1 #
        # self.plot_layouts[name]=(nx,ny)
        # self.indexes[name] = {"paramx": {par:0 for i,par in enumerate(["gaga","2d"])}, "paramy": {par:0 for i,par in enumerate([" 0 ", "par 2", "dd"])}}

        if processor==None:
            processor=self.data_processors[self.current_tab_name]["processor"]

        new=not name in self.tabs_with_plot.keys() #new tab
        if new: #create layout
            self.create_plot_UI(name,tab,processor)

        if processor.two_d:

            tabs=self.tabs_with_plot[name][True]
            self.stacked_widgets[name].setCurrentIndex(1)

            figures = []
            axes = []
            canvases = []

            for TAB in tabs:
                figure, ax, canvas = self.init_figures(TAB,name)
                figures.append(figure)
                axes.append(ax)
                canvases.append(canvas)

            figure, ax, canvas = figures,axes,canvases

        else:
            TAB=self.tabs_with_plot[name][False]
            self.stacked_widgets[name].setCurrentIndex(0)

            figure,ax,canvas=self.init_figures(TAB,name)
            ax=[ax]

        return figure,ax,canvas

    def on_subplot_x_combobox_changed(self,new_param):
        if new_param == "__None__":
            new_axis_elements=[0]
        else:
            new_axis_elements=self.data_processors[self.current_tab_name]["processor"].measurement_parameters[new_param]

        nx=len(new_axis_elements)-len(self.data_processors[self.current_tab_name]["processor"].unselected[new_param])
        self.plot_layouts[self.current_tab_name] = (nx, self.plot_layouts[self.current_tab_name][1])
        self.indexes[self.current_tab_name]["paramx"] = {par: i for i, par in enumerate(set(new_axis_elements)-set(self.data_processors[self.current_tab_name]["processor"].unselected[new_param]))}
        self.handle_selection_change() #to update the combination:parameter name mapping
        #self.combi_idx_x = self.data_processors[self.current_tab_name]["processor"].parameter_map.index(new_param)
        self.paramx[self.current_tab_name]=new_param
        pass

    def on_subplot_y_combobox_changed(self,new_param):
        if new_param == "__None__":
            new_axis_elements = [0]
        else:
            new_axis_elements = self.data_processors[self.current_tab_name]["processor"].measurement_parameters[new_param]
        ny=len(new_axis_elements)-len(self.data_processors[self.current_tab_name]["processor"].unselected[new_param])
        self.plot_layouts[self.current_tab_name] = (self.plot_layouts[self.current_tab_name][0], ny)
        self.indexes[self.current_tab_name]["paramy"] = {par: i for i, par in enumerate(set(new_axis_elements)-set(self.data_processors[self.current_tab_name]["processor"].unselected[new_param]))}
        self.handle_selection_change() #to update the combination:parameter name mapping
        #self.combi_idx_y=self.data_processors[self.current_tab_name]["processor"].parameter_map.index(new_param)
        self.paramy[self.current_tab_name]=new_param
        pass

    def on_difference_combobox_changed(self,new_param):
        new_axis_elements = self.data_processors[self.current_tab_name]["processor"].measurement_parameters[new_param]
        if len(new_axis_elements)!=2:
            print("Error:invalid number of parameters, selection will be ignored.")
            self.data_processors[self.current_tab_name]["processor"].difference_param = "__None__"
        else:
            self.data_processors[self.current_tab_name]["processor"].difference_param=new_param
        pass

    def on_x_axis_param_changed(self,new_param):
        new_param=new_param.text()
        self.data_processors[self.current_tab_name]["processor"].x_axis_param = new_param
        pass

    def on_y_axis_param_changed(self,new_param):
        new_param=new_param.text()
        self.data_processors[self.current_tab_name]["processor"].y_axis_param = new_param
        pass

    def on_z_axis_param_changed(self,new_param):
        new_param=new_param.text()
        z_axis_list_widget=self.z_axis_list_widgets[self.current_tab_name]
        new_params = [Item.text() for Item in z_axis_list_widget.selectedItems()]
        if len(new_params)==0:
            self.data_processors[self.current_tab_name]["processor"].z_axis_param = "__None__"
        else:
            self.data_processors[self.current_tab_name]["processor"].z_axis_param = new_params[0]
        pass

    def on_average_param_changed(self):
        #get the params
        average_widget=self.average_over_list_widgets[self.current_tab_name]
        new_params=[Item.text() for Item in average_widget.selectedItems()]
        self.data_processors[self.current_tab_name]["processor"].average_params = new_params
        pass

    def remove_canvas_and_toolbar(self,parent_tab):
        layout = parent_tab.layout()
        if layout:
            # Iterate through the layout items and remove canvas and toolbar
            for i in reversed(range(layout.count())):  # Iterate in reverse to safely remove items
                item = layout.itemAt(i)
                widget = item.widget()
                if isinstance(widget, (FigureCanvasQTAgg, NavigationToolbar2QT)):
                    layout.takeAt(i)  # Remove the item from the layout
                    widget.deleteLater()  # Safely delete the widget


    def init_figures(self, parent_tab, name):
        # Remove the existing canvas and toolbar, if any
        self.remove_canvas_and_toolbar(parent_tab)

        # Initialize new figures
        fig, ax = plt.subplots(*self.plot_layouts[name])
        canvas = FigureCanvasQTAgg(fig)
        toolbar = NavigationToolbar2QT(canvas, parent_tab)

        # Reuse the existing layout or create one if it doesn't exist
        layout = parent_tab.layout()
        if layout is None:
            layout = QVBoxLayout(parent_tab)
            parent_tab.setLayout(layout)

        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        canvas.mpl_connect("button_press_event", self.on_mouse_press)
        canvas.mpl_connect("button_release_event", self.on_mouse_release)

        if self.plot_layouts[name][0]==1:
            ax=np.array([ax])
        if self.plot_layouts[name][1]==1:
            ax=np.array([ax]).T

        return fig,ax,canvas

    def get_axes(self,combi,tab_name):
        processor=self.data_processors[tab_name]["processor"]
        actual_param_x, actual_param_y = combi[processor.parameter_map.index(self.paramx[self.current_tab_name])], combi[processor.parameter_map.index(self.paramy[self.current_tab_name])]
        x=self.indexes[tab_name]["paramx"][actual_param_x]
        y=self.indexes[tab_name]["paramy"][actual_param_y]

        return self.data_processors[tab_name]["axes"][:,x,y]

    def plot_all_tabs(self):
        for tab in self.data_processors.keys():
            self.plot_data_single(tab)

    def plot_data_single(self, tab_name, fit_name=None,combination=None,clear_plot=False):
        data = self.data_processors[tab_name]
        processor = data["processor"]

        if combination!=None:
            combinations=[combination]
        else:
            combinations=processor.data.keys()

        for i,combination in enumerate(combinations):
            x_data, y_data, z_data = processor.data[combination]
            fitted=None
            if fit_name!=None:
                if combination in processor.fit_results[fit_name]["best_fit"].keys():
                    fitted=processor.fit_results[fit_name]["best_fit"][combination]


            x_data,y_data,z_data=self.run_code(x_data,y_data,z_data,local_scope=locals())

            if processor.two_d: #if 2d plot

                fig_original,fig_fitted,fig_diff=data["figure"]
                ax_original,ax_fitted,ax_diff=self.get_axes(combination,tab_name) #data["axes"]
                canvas_original,canvas_fitted,canvas_diff=data["canvas"]

                if clear_plot:
                    ax_original.clear()
                    ax_fitted.clear()
                    ax_diff.clear()

                #maybe this is useful
                label=processor.combi_to_label[combination]
                L=label.split(", ")
                titlex=""
                titley=""
                for parameter in L[::-1]:
                    if parameter.startswith(self.paramx[self.current_tab_name]+":"):

                        titlex=L.pop(L.index(parameter))
                    if parameter.startswith(self.paramy[self.current_tab_name]+":"):
                        titley=L.pop(L.index(parameter))

                label=" ".join(L)

                # Original Data with Fitted Contours
                contour=ax_original.pcolor(x_data, y_data, z_data, cmap="viridis")
                if tab_name+"original" in self.colorbars.keys():
                    original_colorbar=self.colorbars[tab_name + "original"]
                    original_colorbar.update_normal(contour)
                else:
                    original_colorbar = fig_original.colorbar(contour, ax=ax_original, orientation="vertical")
                    self.colorbars[tab_name + "original"] = original_colorbar

                if fitted is not None:
                    ax_original.contour(x_data, y_data, fitted, colors="red", linestyles="dashed")
                ax_original.set_title(" ".join([titlex,titley]))
                ax_original.set_xlabel(processor.y_axis_param)
                ax_original.set_ylabel(processor.x_axis_param)

                # Fitted Data Plot
                if fitted is not None:
                    contour=ax_fitted.pcolor(x_data, y_data, fitted, cmap="viridis")
                    if tab_name + "fitted" in self.colorbars.keys():
                        fitted_colorbar = self.colorbars[tab_name + "fitted"]
                        fitted_colorbar.update_normal(contour)
                    else:
                        fitted_colorbar = fig_fitted.colorbar(contour, ax=ax_fitted, orientation="vertical")
                        self.colorbars[tab_name + "fitted"] = fitted_colorbar

                ax_fitted.set_title(" ".join([titlex,titley]))
                ax_fitted.set_xlabel(processor.y_axis_param)
                ax_fitted.set_ylabel(processor.x_axis_param)

                # Difference Plot
                if fitted is not None:
                    diff = z_data - fitted
                    contour=ax_diff.pcolor(x_data, y_data, diff, cmap="coolwarm")
                    if tab_name + "diff" in self.colorbars.keys():
                        diff_colorbar = self.colorbars[tab_name + "diff"]
                        diff_colorbar.update_normal(contour)
                    else:
                        diff_colorbar = fig_diff.colorbar(contour, ax=ax_diff, orientation="vertical")
                        self.colorbars[tab_name + "diff"] = diff_colorbar

                ax_diff.set_title(" ".join([titlex,titley]))
                ax_diff.set_xlabel(processor.y_axis_param)
                ax_diff.set_ylabel(processor.x_axis_param)

                for i in range(3):
                    # Collect unique handles and labels from all subplots
                    handles_labels = [ax.get_legend_handles_labels() for ax in data["axes"][i].flat]
                    handles, labels = zip(*handles_labels)
                    unique_handles_labels = {label: handle for handle, label in zip(sum(handles, []), sum(labels, []))}

                    # Add a single legend for the figure
                    #data["figure"][i].legend(unique_handles_labels.values(), unique_handles_labels.keys(), loc="upper center", ncol=4, fontsize=10)
                    data["figure"][i].subplots_adjust(left=0.05, right=0.99, top=0.9, bottom=0.1)


                canvas_original.draw()
                canvas_fitted.draw()
                canvas_diff.draw()


            else:
                ax = self.get_axes(combination,tab_name)[0]
                if clear_plot:
                    ax.clear()

                label=processor.combi_to_label[combination]
                L=label.split(", ")
                titlex=""
                titley=""
                for parameter in L[::-1]:
                    if parameter.startswith(self.paramx[self.current_tab_name]+":"):

                        titlex=L.pop(L.index(parameter))
                    if parameter.startswith(self.paramy[self.current_tab_name]+":"):
                        titley=L.pop(L.index(parameter))

                label=" ".join(L)

                ax.plot(x_data, y_data, ".-", label=label)
                if fitted is not None:
                    ax.plot(x_data, fitted, label=["Fit " + label], color="red")
                    if self.show_uncertainity:
                        uncertainty= processor.fit_results[fit_name]["result"][combination].eval_uncertainty(x=x_data)
                        ax.fill_between(x_data, fitted - uncertainty, fitted + uncertainty,
                                     color='gray', alpha=0.5, label='1-sigma uncertainty')

                #ax.legend()
                ax.set_title(" ".join([titlex,titley]))
                ax.set_xlabel(processor.x_axis_param)
                ax.set_ylabel(processor.y_axis_param)

                # Collect unique handles and labels from all subplots
                handles_labels = [ax.get_legend_handles_labels() for ax in data["axes"].flat]
                handles, labels = zip(*handles_labels)
                unique_handles_labels = {label: handle for handle, label in zip(sum(handles, []), sum(labels, []))}

                if len(data["figure"].legends):
                    #print(len(data["figure"].legends))
                    data["figure"].legends[0].remove()  # Remove the first legend in the list

                # Add a single legend for the figure
                data["figure"].legend(unique_handles_labels.values(), unique_handles_labels.keys(),
                           loc="upper center", ncol=self.label_ncols, fontsize=self.label_frontsize)

                # Adjust layout to make room for the legend
                #data["figure"].tight_layout(rect=[0, 0, 1, 0.9])
                data["figure"].subplots_adjust(left=0.10, right=0.99, top=0.9, bottom=0.1)

                data["canvas"].draw()

            processor.progress_bar.setValue(int((i+1) / len(combinations) * 100))


    def perform_fit(self):
        current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        self.clear_plot(current_tab_name)
        parameter_combinations=self.data_processors[current_tab_name]["processor"].data.keys()
        if current_tab_name not in self.data_processors:
            print("Error: tab does not have a data_processor")
            return

        selected_display_name = self.fit_combobox.currentText()

        # Retrieve selected fit from FitManager
        selected_fit = next(
            (name for name, data in self.fit_manager.fits.items() if data["display_name"] == selected_display_name),
            None
        )

        if not selected_fit:
            return

        fit_data = self.fit_manager.fits[selected_fit]
        manager_expression = fit_data["machine_expression"]

        if self.current_literal.replace(" ", "") != manager_expression:
            # The user-defined literal is different from the FitManager
            # Prompt for a new function name
            new_function_name, ok = QInputDialog.getText(
                self, "New Fit Function", "Enter a name for the new fit function:"
            )
            if not ok or not new_function_name.strip():
                print("Fit canceled, no new name provided.")
                return

            new_function_name = new_function_name.strip()
            # Add the new fit function to FitManager and the ComboBox
            self.fit_manager.add_fit_function(new_function_name, self.current_literal, new_function_name)
            #self.fit_manager.prepare_parameters(processor.data.keys())
            self.fit_combobox.addItem(new_function_name)
            self.fit_combobox.setCurrentText(new_function_name)
            selected_fit = new_function_name

        processor = self.data_processors[current_tab_name]["processor"]
        processor.prepare_fit_dataframe(list(self.fit_manager.fits[selected_fit]["parameters_blueprint"].keys()))

        x_axis_list=self.x_axis_list_widgets[self.current_tab_name]
        y_axis_list=self.y_axis_list_widgets[self.current_tab_name]
        z_axis_list=self.z_axis_list_widgets[self.current_tab_name]

        selected_item_y = y_axis_list.currentItem()
        selected_text_y = selected_item_y.text() if selected_item_y else None
        selected_item_z = z_axis_list.currentItem()
        selected_text_z = selected_item_z.text() if selected_item_z else None
        selected_item_x = x_axis_list.currentItem()
        selected_text_x = selected_item_x.text() if selected_item_x else None

        y_axis_list.clear()
        x_axis_list.clear()
        z_axis_list.clear()

        y_axis_list.addItems(list(processor.measurement_observations.keys()))
        y_axis_list.addItems(list(processor.measurement_parameters.keys()))
        y_axis_list.addItems(list(self.fit_manager.fits[selected_fit]["parameters_blueprint"].keys()))

        x_axis_list.addItems(list(processor.measurement_parameters.keys()))
        x_axis_list.addItems(list(self.fit_manager.fits[selected_fit]["parameters_blueprint"].keys()))

        z_axis_list.addItems(list(processor.measurement_observations.keys()))
        z_axis_list.addItems(list(self.fit_manager.fits[selected_fit]["parameters_blueprint"].keys()))

        # Restore the selection if the item still exists
        for selected_text,list_widget in zip([selected_text_x,selected_text_y,selected_text_z],[x_axis_list,y_axis_list,z_axis_list]):
            if selected_text and selected_text in (list(processor.measurement_observations.keys())+list(processor.measurement_parameters.keys())+list(self.fit_manager.fits[selected_fit]["parameters_blueprint"].keys())):
                matching_items = list_widget.findItems(selected_text, Qt.MatchExactly)
                if matching_items:
                    list_widget.setCurrentItem(matching_items[0])

        for combination in parameter_combinations:

            self.fit_manager.prepare_parameters(processor.data.keys())
            success = processor.perform_fit(selected_fit,combination, self.fit_manager,self)

            if success:
                self.plot_data_single(current_tab_name, fit_name=selected_fit,combination=combination,clear_plot=False)
            else:
                print("Fit failed for combination ", combination)

        fit_results = processor.fit_results[selected_fit]
        self.update_parameter_table(fit_results["parameters"])

    def clear_plot(self,tab):
        axes=self.data_processors[tab]["axes"].flatten()
        for ax in axes:
            ax.clear()

    def on_tab_changed(self, index):
        # Save the current tab's state abd Get the new tab's name
        current_tab_name = self.tab_widget.tabText(self.previous_tab_index)

        if current_tab_name:
            try:
                self.save_tab_state(current_tab_name)
            except Exception as e:
                print("error saving tab state, ",e)

        new_tab_name = self.tab_widget.tabText(index)

        self.fit_manager.prepare_parameters(self.data_processors[new_tab_name]["processor"].data.keys())
        self.current_tab_name = new_tab_name
        self.restore_tab_state(new_tab_name)


        # Update previous_tab_index
        self.previous_tab_index = index

    def update_table_size(self,nlines):
        self.parameter_table.setColumnCount(1+nlines*4)
        self.parameter_table.setHorizontalHeaderLabels(["Parameter"]+[ "Initial Guess", "Fitted Value", "Vary","Set initial guess"]*nlines)

    def save_tab_state(self, tab_name):
        """
        Save the current state of the tab, including literal, parameters, and selected fit.
        """
        state = {
            "fit_literal": self.fit_literal_input.text(),
            "parameters": self.get_current_table_parameters(tab_name),
            "selected_fit": self.fit_combobox.currentText(),
        }
        self.tab_states[tab_name] = state

    def restore_tab_state(self, tab_name):
        """
        Restore the saved state of the tab, or reset to default values if no state is saved.
        """
        if tab_name in self.tab_states:
            state = self.tab_states[tab_name]
            # Restore the literal
            self.fit_literal_input.setText(state["fit_literal"])

            # Restore the selected fit function
            self.fit_combobox.setCurrentText(state["selected_fit"])

            # Restore the parameter table
            self.update_parameter_table(state["parameters"],tab_name)
        else:
            # Default values if no state is saved
            fit_name = self.fit_combobox.currentText()
            fit_data = self.fit_manager.fits[fit_name]
            self.fit_literal_input.setText(fit_data["expression"])
            try:
                self.update_parameter_table(fit_data["parameters"])
            except Exception as e:
                print("error restoring tab state:",e)

    def get_current_table_parameters(self,name=None):
        """
        Retrieve the current parameter table values as a dictionary,
        including the parameter name, initial guess, fitted value, and vary state.
        """
        n_cols=self.parameter_table.columnCount()
        n_params=int((n_cols-1)/4)
        Parameters_dict={}
        for k in range(n_params):
            param_combi=self.to_combi(self.parameter_table.cellWidget(0, k*4+1).text().replace("<font color='black'>","").replace("</font>",""),name)
            parameters = {}
            for row in range(1,self.parameter_table.rowCount()):

                param_name = self.parameter_table.item(row, 0).text()
                initial_guess = float(self.parameter_table.item(row, k*4+1).text())

                # Retrieve fitted value, handling empty cells gracefully
                fitted_value_item = self.parameter_table.item(row, k*4+2)
                if fitted_value_item and fitted_value_item.text():
                    fitted_value = float(fitted_value_item.text())
                else:
                    fitted_value = None  # Default to None if no value is present

                # Retrieve vary state from the checkbox
                vary = self.parameter_table.cellWidget(row, k*4+3).isChecked()

                # Save the values in a dictionary
                parameters[param_name] = {
                    "initial_guess": initial_guess,
                    "fitted_value": fitted_value,
                    "vary": vary,
                    "std":fitted_value_item.toolTip()
                }
            Parameters_dict[param_combi]=parameters

        return Parameters_dict

    def to_combi(self,input,name=None):
        if name==None:
            name=self.current_tab_name

        real_combi=self.data_processors[name]["processor"].correspondences(label=input)
        return real_combi

    def update_parameter_table(self, parameters,tab_name=None): # it wants the data under the format: {combination: {the parameters}}

        self.update_table_size(len(parameters))
        label = QLabel("")
        label.setStyleSheet("background-color: aqua;")
        self.parameter_table.setCellWidget(0, 0, label)
        for k,combi in enumerate(parameters.keys()):
            if tab_name == None:
                tab_name = self.current_tab_name
            ParaMeters=parameters[combi]
            self.parameter_table.setRowCount(len(ParaMeters)+1)
            if len(ParaMeters)==0:
                return
            combi_label=self.data_processors[tab_name]["processor"].correspondences(combi=combi)
            label = QLabel(f"<font color='black'>{combi_label}</font>")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("background-color: aqua;")
            self.parameter_table.setCellWidget(0, 4 * k + 1, label)
            self.parameter_table.setSpan(0, 4 * k + 1, 1, 4)


            for row, (param, data) in enumerate(ParaMeters.items()):
                row=row+1
                self.parameter_table.setItem(row, 0, QTableWidgetItem(param))
                self.parameter_table.setItem(row, 4*k+1, QTableWidgetItem(str(data["initial_guess"])))
                item=QTableWidgetItem(str(data["fitted_value"] or ""))
                item.setToolTip(str(data["std"] or ""))
                self.parameter_table.setItem(row, 4*k+2, item)
                checkbox = QCheckBox()
                checkbox.setChecked(data["vary"])
                checkbox.stateChanged.connect(lambda state, p=param, combi=combi: self.update_vary_state(p, state,combi))
                self.parameter_table.setCellWidget(row, 4*k+3, checkbox)
                checkbox = QCheckBox()
                self.parameter_table.setCellWidget(row, 4*k+4, checkbox)

    def on_literal_change(self, new_literal):

        self.current_literal = new_literal
        # Dynamically parse parameters without modifying FitManager
        try:
            params,use_y=extract_parameters(new_literal)
            parsed_parameters = {
                param: {"initial_guess": 1.0, "fitted_value": None, "vary": True, "std":None}
                for param in params
            }

            tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
            if tab_name not in self.data_processors:
                return

            processor = self.data_processors[tab_name]["processor"]
            selected_display_name = self.fit_combobox.currentText()
            selected_fit = next(
                (name for name, data in self.fit_manager.fits.items() if data["display_name"] == selected_display_name),
                None
            )
            if not selected_fit:
                return

            if selected_fit:

                # Retrieve saved fit data from DataProcessor
                if selected_fit in processor.fit_results.keys():
                    existing_parameters = processor.fit_results[selected_fit]["parameters"]
                else:
                    existing_parameters = self.fit_manager.fits[selected_fit]["parameters"]
                # Keep existing values for parameters that match #Maybe we need to change this also

                for combi in existing_parameters.keys():
                    for param, data in parsed_parameters.items():
                        if not param in existing_parameters[combi]:
                            existing_parameters[combi][param]=copy.deepcopy(parsed_parameters[param]) #add the new ones while keeping the old ones unchanged

                    #and remove the missing ones
                    to_delete=[]
                    for param in existing_parameters[combi]:
                        if param not in parsed_parameters.keys():
                            to_delete.append(param)

                    for param in to_delete:
                        existing_parameters[combi].pop(param)

                self.update_parameter_table(existing_parameters)
        except Exception as e:
            print(f"Error parsing parameters: {e}")

    def on_fit_selection_changed(self, display_name):
        selected_fit = next(
            (name for name, data in self.fit_manager.fits.items() if data["display_name"] == display_name),
            None
        )
        if not selected_fit:
            return
        fit_data = self.fit_manager.fits[selected_fit]
        self.fit_literal_input.setText(fit_data["expression"])
        self.update_parameter_table(fit_data["parameters"])

    def on_table_item_changed(self, item):
        if (item.column()%4 == 1) and (item.row()!=0):  # Initial guess column
            row = item.row()
            column = item.column()
            param_index=int((column-1)/4)
            try:
                combi = self.to_combi(self.parameter_table.cellWidget(0, param_index * 4 + 1).text().replace("<font color='black'>","").replace("</font>",""))
                param_name = self.parameter_table.item(row, 0).text()

                new_value = float(item.text())
                self.update_initial_guess(param_name, new_value,combi)
            #except ValueError:
            #     print(f"Invalid initial guess for {param_name}")
            except KeyError:
                 pass

    def update_initial_guess(self, param_name, new_value,combi):
        selected_display_name = self.fit_combobox.currentText()
        selected_fit = next(
            (name for name, data in self.fit_manager.fits.items() if data["display_name"] == selected_display_name),
            None
        )
        if selected_fit:
            try:
                self.fit_manager.fits[selected_fit]["parameters"][combi][param_name]["initial_guess"] = new_value
            except Exception as e:
                print("error updating initial guess: ",e)
        pass


    def update_vary_state(self, param_name, state,combi):
        selected_display_name = self.fit_combobox.currentText()
        selected_fit = next(
            (name for name, data in self.fit_manager.fits.items() if data["display_name"] == selected_display_name),
            None
        )
        if selected_fit:
            self.fit_manager.fits[selected_fit]["parameters"][combi][param_name]["vary"] = state == Qt.Checked
        pass

    def on_mouse_press(self, event):
        """Handle mouse press events."""
        if event.inaxes:
            x, y = event.xdata, event.ydata
            self.mouse_x, self.mouse_y =x,y
            #print(f"Mouse pressed at: x={x:.2f}, y={y:.2f}")

    def on_mouse_release(self, event):
        """Handle mouse release events."""
        if event.inaxes:

            axes=event.inaxes

            x, y = event.xdata, event.ydata
            #print(f"Mouse released at: x={x:.2f}, y={y:.2f}")

            # current_tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
            # axes = self.data_processors[self.current_tab_name]["axes"]
            #
            # if self.data_processors[self.current_tab_name]["processor"].two_d: #if 2d plot
            #     axes=axes[0]

            x_range=np.diff(axes.get_xlim())
            y_range=np.diff(axes.get_ylim())

            if abs(self.mouse_x-x)>0.01*x_range:
                x= abs(self.mouse_x-x)
            if abs(self.mouse_y-y)>0.01*y_range:
                x= abs(self.mouse_y-y)

            for row in range(1,self.parameter_table.rowCount()):
                for k in range(int((self.parameter_table.columnCount()-1)/4)):
                    vary = self.parameter_table.cellWidget(row, k*4+4).isChecked()
                    if vary:
                        param_name = self.parameter_table.item(row, 0).text()
                        self.parameter_table.cellWidget(row, k*4+4).setChecked(False)
                        if "y" in param_name:
                            self.parameter_table.setItem(row, k*4+1, QTableWidgetItem(str(y)))
                        else:
                            self.parameter_table.setItem(row, k*4+1, QTableWidgetItem(str(x)))

    def open_measurements_viewer(self):
        """Open the measurements viewer window."""
        if self.current_tab_name in self.setters.keys():
            setter=self.setters[self.current_tab_name]
        else:
            processor=self.data_processors[self.current_tab_name]["processor"]
            processor.make_trace_to_list()
            setter = ParameterTableApp(    parameters = [processor.measurement_parameters[key] for key in processor.measurement_parameters.keys()],
                                           processor=processor,
                                           name=self.current_tab_name
    )
            self.setters[self.current_tab_name] =setter

        setter.show()


    @staticmethod
    def generate_sample_measurements():
        """
        Generate sample measurement data for demonstration.
        Each measurement is a dictionary with parameters and traces.
        """
        measurements = []
        for i in range(10):  # 10 measurements
            params = {"param1": f"value{i}", "param2": f"value{i * 2}"}
            counts = [np.random.poisson(lam=10 + j, size=100) for j in range(3)]  # 3 histograms per measurement
            measurements.append({"parameters": params, "counts": counts})
        return measurements

class ParameterTableApp(QMainWindow):
    def __init__(self, parameters,processor,name):
        super().__init__()
        self.processor=processor
        self.parameters = parameters
        self.df = processor.df
        self.concatenated_trace = []  # To store the concatenated trace
        self.histogram_controls = []  # To store histogram controls for callbacks

        self.control_dict = {}  # Dictionary to store control settings
        self.num_histograms = len(self.processor.indexes)

        self.init_ui(name)
        self.initialize_control_dict()
        self.handle_selection_change()


    def init_ui(self,name):
        self.setWindowTitle(f"Threshold setter for {name}")

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a splitter for table and plot area
        self.splitter = QSplitter(Qt.Vertical)
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(len(self.parameters))
        self.table_widget.setHorizontalHeaderLabels([list(self.processor.measurement_parameters.keys())[i] for i in range(len(self.parameters))])

        # Set selection mode and behavior
        self.table_widget.setSelectionMode(QTableWidget.MultiSelection)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectItems)

        # Determine the maximum number of rows needed
        max_rows = max(len(values) for values in self.parameters)
        self.table_widget.setRowCount(max_rows)

        # Populate the table
        for col, values in enumerate(self.parameters):
            for row, value in enumerate(values):
                self.table_widget.setItem(row, col, QTableWidgetItem(str(value)))

        # Select all cells at the start
        self.select_all_cells()

        # Connect selection changes
        self.table_widget.itemSelectionChanged.connect(self.conditional_handle_selection_change)

        self.update_behavior=QWidget()
        self.update_layout=QHBoxLayout(self.update_behavior)

        self.update_now_checkbox=QCheckBox("Immediate update")
        self.update_now_button=QPushButton("Update now!")

        self.update_now_button.clicked.connect(self.handle_selection_change)

        self.update_layout.addWidget(self.update_now_checkbox)
        self.update_layout.addWidget(self.update_now_button)

        self.splitter.addWidget( self.update_behavior)

        # Add table widget to splitter
        self.splitter.addWidget(self.table_widget)

        # Create plot area
        self.plot_area = QWidget()
        self.plot_layout = QGridLayout(self.plot_area)
        self.splitter.addWidget(self.plot_area)

        # Add splitter to layout
        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        central_widget.setLayout(layout)

        # Update UI
        self.create_apply_button()

    def initialize_control_dict(self):
        """
        Initialize the control dictionary with all possible combinations as keys
        and default control values.
        """
        # Get selected values from the table
        selected_values = {}
        for col in range(self.table_widget.columnCount()):
            parameter = self.table_widget.horizontalHeaderItem(col).text()
            selected_values[col + 1] = [
                self.table_widget.item(row, col).text()
                for row in range(self.table_widget.rowCount())
                if self.table_widget.item(row, col)
            ]

        # Use compute_ordered_combinations to get all possible ordered combinations
        all_combinations = self.compute_ordered_combinations(selected_values, generate_all=True)

        # Initialize control_dict with default values for each combination
        self.control_dict={}
        for combination in all_combinations:
            self.control_dict[combination] = {}
            for i in range(self.num_histograms):
                analysis_info = self.processor.ana_seq[self.processor.indexes[i + 1]]
                self.control_dict[combination][i]={
                "slider": analysis_info[2],  # Default slider value
                "combo_box": analysis_info[1],  # Default combo box value
                "num1_input": analysis_info[4],  # Default spinbox value
                "num2_input": analysis_info[4],  # Default spinbox value
            }

    def conditional_handle_selection_change(self):
        if self.update_now_checkbox.isChecked():
            self.handle_selection_change()

    def create_apply_button(self):
        # Container widget for buttons
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)

        # Apply button
        apply_button = QPushButton("Apply (only saves, nothing is calculated)")
        apply_button.clicked.connect(self.save_controls)
        button_layout.addWidget(apply_button)

        # Recalculate button
        recalculate_button = QPushButton("Recalculate")
        recalculate_button.clicked.connect(self.recalculate)
        button_layout.addWidget(recalculate_button)

        # Add the button container to the splitter
        self.splitter.addWidget(button_container)

    def recalculate(self):
        self.save_controls()
        self.processor.recalculate(self.control_dict)

    def save_controls(self):
        """
        Save the current control states into the control dictionary for each selected combination.
        """
        selected_combinations = self.get_selected_combinations()

        for combination in selected_combinations:
            for idx, controls in enumerate(self.histogram_controls):
                slider_value = controls[3].value()
                combo_box_value = controls[6].currentText()
                num1_value = controls[4].value()
                num2_value = controls[5].value()

                # Save values to the dictionary for the specific combination
                if combination not in self.control_dict:
                    self.control_dict[combination] = {}  # Ensure combination exists in control_dict

                self.control_dict[combination][idx] = {
                    "slider": slider_value,
                    "combo_box": combo_box_value,
                    "num1_input": num1_value,
                    "num2_input": num2_value,
                }

        #print("Controls saved:")

    def apply_controls(self):
        """
        Apply the saved control states to the histograms based on current selected combinations.
        """
        selected_combinations = self.get_selected_combinations()

        for idx, combination in enumerate(selected_combinations):
            if combination in self.control_dict:
                saved_values = self.control_dict[combination]

                for hist_idx, controls in enumerate(self.histogram_controls):
                    if hist_idx in saved_values:
                        controls[3].setValue(saved_values[hist_idx]["slider"])
                        controls[6].setCurrentText(saved_values[hist_idx]["combo_box"])
                        controls[4].setValue(saved_values[hist_idx]["num1_input"])
                        controls[5].setValue(saved_values[hist_idx]["num2_input"])

    def get_majority_vote(self, selected_combinations):
        """
        Determine the majority vote for control values for each histogram index.
        :param selected_combinations: List of ordered combinations currently selected.
        :return: A dictionary where keys are histogram indices (idx) and values are dictionaries
                 containing the majority values for slider, combo_box, num1_input, and num2_input.
        """
        # Initialize a structure to store values per index
        index_controls = {}

        # Collect values from the control_dict for the selected combinations
        for combination in selected_combinations:
            if combination in self.control_dict:
                for hist_idx, controls in self.control_dict[combination].items():
                    if hist_idx not in index_controls:
                        index_controls[hist_idx] = {
                            "slider": [],
                            "combo_box": [],
                            "num1_input": [],
                            "num2_input": []
                        }
                    index_controls[hist_idx]["slider"].append(controls["slider"])
                    index_controls[hist_idx]["combo_box"].append(controls["combo_box"])
                    index_controls[hist_idx]["num1_input"].append(controls["num1_input"])
                    index_controls[hist_idx]["num2_input"].append(controls["num2_input"])

        # Helper function to determine the majority vote
        def majority_vote(values):
            if not values:
                return None  # Return None if no values
            return max(set(values), key=values.count)

        # Compute the majority for each index
        majority_by_index = {}
        for hist_idx, control_values in index_controls.items():
            majority_by_index[hist_idx] = {
                "slider": majority_vote(control_values["slider"]),
                "combo_box": majority_vote(control_values["combo_box"]),
                "num1_input": majority_vote(control_values["num1_input"]),
                "num2_input": majority_vote(control_values["num2_input"]),
            }

        return majority_by_index

    def create_test_dataframe(self, parameters):
        """Create a test DataFrame with all combinations accessible from the table and random trace lists."""
        # Generate ordered combinations using the same logic as the table
        selected_values = {i: parameters[i] for i in range(len(parameters))}
        ordered_combinations = self.compute_ordered_combinations(selected_values, generate_all=True)

        # Create a DataFrame
        df = pa.DataFrame(ordered_combinations, columns=[f"Param {i + 1}" for i in range(len(parameters))])

        # Assign a random trace to each combination
        def generate_trace():
            trace_length = random.choice([30, 60, 90])  # Length must be a multiple of 30
            return [random.randint(0, 100) for _ in range(trace_length)]

        df["Trace"] = [generate_trace() for _ in range(len(ordered_combinations))]
        df.set_index([f"Param {i + 1}" for i in range(len(parameters))], inplace=True)
        return df

    def select_all_cells(self):
        """Select all non-empty cells in the table."""
        for col in range(self.table_widget.columnCount()):
            for row in range(self.table_widget.rowCount()):
                item = self.table_widget.item(row, col)
                if item and item.text():
                    item.setSelected(True)


    def handle_selection_change(self):

        datatypes = self.processor.df._Datatypes

        # Compute selected combinations and update concatenated trace
        selected_values = {list(self.processor.measurement_parameters.keys())[col]: [] for col in range(self.table_widget.columnCount())}
        for item in self.table_widget.selectedItems():
            if item.text():
                col = item.column()
                col_name = list(self.processor.measurement_parameters.keys())[col]
                selected_values[col_name].append(datatypes[col_name].type(item.text()))

        for col in range(self.table_widget.columnCount()):
            col_name = list(self.processor.measurement_parameters.keys())[col]
            if not selected_values[col_name]:
                for row in range(self.table_widget.rowCount()):
                    item = self.table_widget.item(row, col)
                    if item and item.text():
                        item.setSelected(True)
                        selected_values[col_name].append(datatypes[col_name].type(item.text()))

        # Deselect empty cells immediately
        for item in self.table_widget.selectedItems():
            if not item.text():
                item.setSelected(False)

        combinations = self.compute_ordered_combinations(selected_values)
        self.concatenated_trace = []
        for i,combination in enumerate(combinations):
            # Dictionary with desired values
            keys=list(self.processor.measurement_parameters.keys())
            desired_values = {keys[i]: combination[i] for i in range(len(combination))}

            # Filter for the parameters to match
            filtered_df = self.df.loc[(self.df[list(desired_values)] == pa.Series(desired_values)).all(axis=1)]

            if len(filtered_df)==1:
                try:
                    trace=list(filtered_df.Trace)[0]
                    self.concatenated_trace.extend(trace)
                except Exception as e:
                    print("ERROR when concatenating lists: ",e)

            self.processor.progress_bar.setValue(int((i+1)/len(combinations)*100))

        #print(self.concatenated_trace)
        # Generate histograms
        self.generate_histograms()

    # In the generate_histograms method, update layout logic
    def generate_histograms(self):
        # Clear the existing layout in the plot area
        while self.plot_layout.count():
            item = self.plot_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        concatenated_trace = self.concatenated_trace

        # Determine selected combinations
        selected_combinations = self.get_selected_combinations()
        self.histogram_controls = []

        # Calculate rows and columns for grid layout
        grid_size = int(np.ceil(np.sqrt(self.num_histograms)))
        for idx in range(self.num_histograms):
            trace_data = concatenated_trace[idx::self.num_histograms]

            # Use majority rule to get initial values
            initial_values = self.get_majority_vote(selected_combinations)

            widget, red_line, blue_line_1, blue_line_2, slider, num1_input, num2_input, combo_box, normal,positive,negative = self.create_histogram_plot(
                trace_data, idx, self.update_callback
            )
            self.histogram_controls.append(
                (red_line, blue_line_1, blue_line_2, slider, num1_input, num2_input, combo_box, normal,positive,negative))

            analysis_info=self.processor.ana_seq[self.processor.indexes[idx+1]]
            threshold=analysis_info[2]
            rule=analysis_info[1]
            exclusion_zone=analysis_info[4]


            # Apply initial values to controls
            slider.setValue(initial_values.get(idx, {}).get("slider", threshold))
            combo_box.setCurrentText(initial_values.get(idx, {}).get("combo_box", rule))
            num1_input.setValue(initial_values.get(idx, {}).get("num1_input", exclusion_zone))
            num2_input.setValue(initial_values.get(idx, {}).get("num2_input", exclusion_zone))

            # Add histogram to the grid layout
            row, col = divmod(idx, grid_size)
            self.plot_layout.addWidget(widget, row, col)

        # Force layout update
        self.plot_area.setLayout(self.plot_layout)

    def get_selected_combinations(self):
        """
        Get the currently selected parameter-value combinations from the table using compute_ordered_combinations.
        :return: A list of tuples representing the selected ordered combinations.
        """
        selected_values = {}
        for col in range(self.table_widget.columnCount()):
            parameter = self.table_widget.horizontalHeaderItem(col).text()
            selected_values[col + 1] = [
                self.processor.df._Datatypes[parameter].type(self.table_widget.item(row, col).text())
                for row in range(self.table_widget.rowCount())
                if self.table_widget.item(row, col) and self.table_widget.item(row, col).isSelected()
            ]

        return self.compute_ordered_combinations(selected_values)

    def create_histogram_plot(self, data, idx, update_callback):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create pyqtgraph histogram
        plot_widget = pg.PlotWidget()
        y, x = np.histogram(data, bins=np.linspace(0,np.max(data)+1,np.max(data)+2)-0.001)
        bar_item = pg.BarGraphItem(x=x[:-1], height=y, width=np.diff(x), brush='gray')
        bar_item.DATA=np.array(data)
        bar_item_positive = pg.BarGraphItem(x=x[:-1], height=0, width=np.diff(x), brush=(255, 165, 0, 150))

        bar_item_negative = pg.BarGraphItem(x=x[:-1], height=0, width=np.diff(x), brush=(51, 102, 255, 150))
        plot_widget.addItem(bar_item)
        plot_widget.addItem(bar_item_positive)
        plot_widget.addItem(bar_item_negative)

        # Add a legend in the top-right corner
        legend = pg.LegendItem(offset=(-20, 10))  # Top-right corner
        legend.setParentItem(plot_widget.graphicsItem())

        # Add a legend entry using a dummy scatter plot item
        dummy_item = pg.ScatterPlotItem(pen=pg.mkPen(None), brush="gray", size=10)
        legend.addItem(dummy_item, "data")  # Add label to legend

        # Add a legend entry using a dummy scatter plot item
        dummy_item = pg.ScatterPlotItem(pen=pg.mkPen(None), brush=(255, 165, 0, 150), size=10)
        legend.addItem(dummy_item, "filtered data")  # Add label to legend

        # Add red vertical line
        red_line = pg.InfiniteLine(pos=np.mean(data), angle=90, pen=pg.mkPen("red", width=2))
        plot_widget.addItem(red_line)

        # Add blue lines (initially hidden)
        blue_line_1 = pg.InfiniteLine(angle=90, pen=pg.mkPen("blue", width=2))
        blue_line_2 = pg.InfiniteLine(angle=90, pen=pg.mkPen("blue", width=2))
        plot_widget.addItem(blue_line_1)
        plot_widget.addItem(blue_line_2)
        blue_line_1.setVisible(False)
        blue_line_2.setVisible(False)

        # Set axis labels and title
        plot_widget.setLabel('bottom', "Counts")
        plot_widget.setLabel('left', "Occurrences")
        plot_widget.setTitle(f"SSR {idx+1}")

        # Slider and controls
        controls_layout = QHBoxLayout()

        # Add combo box for conditions
        combo_box = QComboBox()
        combo_box.addItems([">", "<"])
        combo_box.currentIndexChanged.connect(
            lambda: update_callback(slider.value(), red_line, blue_line_1, blue_line_2, idx))

        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, max(data))
        slider.setValue(int(np.mean(data)))
        slider.valueChanged.connect(lambda value: update_callback(value, red_line, blue_line_1, blue_line_2, idx))

        # Exclusion zone controls
        exclusion_label = QLabel("EZ")
        num1_input = QSpinBox()
        num2_input = QSpinBox()
        num1_input.valueChanged.connect(
            lambda: update_callback(slider.value(), red_line, blue_line_1, blue_line_2, idx))
        num2_input.valueChanged.connect(
            lambda: update_callback(slider.value(), red_line, blue_line_1, blue_line_2, idx))

        # Add widgets to layout
        controls_layout.addWidget(QLabel("Rule: 1 if"))
        controls_layout.addWidget(combo_box)  # Add combo box
        controls_layout.addWidget(QLabel("Threshold"))
        controls_layout.addWidget(slider)
        controls_layout.addWidget(exclusion_label)
        controls_layout.addWidget(QLabel("-"))
        controls_layout.addWidget(num1_input)
        controls_layout.addWidget(QLabel("+"))
        controls_layout.addWidget(num2_input)

        layout.addWidget(plot_widget)
        layout.addLayout(controls_layout)

        return widget, red_line, blue_line_1, blue_line_2, slider, num1_input, num2_input, combo_box,bar_item,bar_item_positive,bar_item_negative

    def update_callback(self, slider_value, red_line, blue_line_1, blue_line_2, idx):
        num1_input = self.histogram_controls[idx][4]
        num2_input = self.histogram_controls[idx][5]
        combo_box = self.histogram_controls[idx][6]  # Access combo box

        # Handle combo box condition (">" or "<")
        condition = combo_box.currentText()

        # Update the red line position
        red_line.setValue(slider_value)

        # Update blue lines based on exclusion zones
        if num1_input.value() > 0:
            blue_line_1.setValue(slider_value - num1_input.value())
            blue_line_1.setVisible(True)
        else:
            blue_line_1.setVisible(False)

        if num2_input.value() > 0:
            blue_line_2.setValue(slider_value + num2_input.value())
            blue_line_2.setVisible(True)
        else:
            blue_line_2.setVisible(False)

        # You can add condition logic here if needed for future functionality
        self.update_conditional_histograms()

    def update_conditional_histograms(self):
        if len(self.histogram_controls)>0:
            init_msk=np.full(len(self.histogram_controls[0][7].DATA),True)
        else:
            return

        for i,controls in enumerate(self.histogram_controls):
            if self.processor.ana_seq[i][0]=="init":

                slider_value = controls[3].value()
                combo_box_value = controls[6].currentText()
                num1_value = controls[4].value()
                num2_value = controls[5].value()
                data=controls[7].DATA

                rule = combo_box_value
                rule_neg = ["<", ">"][rule == "<"]  # switch rule

                num = [num1_value,num2_value][rule == "<"]
                msk = eval(
                    f'data {rule}= ({slider_value} {["+", "-"][rule == ">"]} {num})')

                # num_neg = [num1_value,num2_value][rule_neg == "<"]
                # msk_neg = eval(
                #     f'i_ssr {rule_neg} {slider_value} {["+", "-"][rule_neg == "<"]} {num_neg}')

                init_msk=init_msk & msk

        for i,controls in enumerate(self.histogram_controls):
            try:
                data = controls[7].DATA
                y, x = np.histogram(data[init_msk], bins=np.linspace(0,np.max(data)+1,np.max(data)+2)-0.001)
                controls[8].setOpts(x=x[:-1], height=y,width=np.diff(x))
            except Exception as e:
                print("Error when updating histograms:", e)

            #bar_item = pg.BarGraphItem(x=x[:-1], height=y, width=np.diff(x), brush='gray')
            #bar_item_positive = pg.BarGraphItem(x=x[:-1], height=0, width=np.diff(x), brush=(255, 165, 0, 150))
            #bar_item_negative = pg.BarGraphItem(x=x[:-1], height=0, width=np.diff(x), brush=(51, 102, 255, 150))

    def compute_ordered_combinations(self, selected_values, generate_all=False):
        """Compute ordered combinations and optionally generate all possible combinations."""
        if generate_all:
            # Generate all combinations for the DataFrame creation
            raw_combinations = list(product(*[values for values in selected_values.values()]))
        else:
            # Generate combinations based on current selection
            raw_combinations = list(product(
                *[[(col, value) for value in values] for col, values in selected_values.items()]))

        if generate_all:
            return [tuple(combination) for combination in raw_combinations]

        ordered_combinations = []
        for combination in raw_combinations:
            # Convert combination to a tuple
            ordered_combinations.append(tuple(value for _, value in combination))
        return ordered_combinations

class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlight_rules = []
        self.setup_highlight_rules()

    def setup_highlight_rules(self):
        """Defines syntax highlighting rules."""
        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("blue"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "def", "class", "if", "else", "elif", "while", "for", "break", "continue", "return",
            "try", "except", "finally", "import", "from", "as", "pass", "raise", "with", "yield",
            "and", "or", "not", "is", "in", "lambda", "None", "True", "False"
        ]
        for keyword in keywords:
            pattern = QRegExp(rf'\b{keyword}\b')
            self.highlight_rules.append((pattern, keyword_format))

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("purple"))
        self.highlight_rules.append((QRegExp(r'\b\w+(?=\()'), function_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("red"))
        self.highlight_rules.append((QRegExp(r'"[^"\\]*(\\.[^"\\]*)*"'), string_format))
        self.highlight_rules.append((QRegExp(r"'[^'\\]*(\\.[^'\\]*)*'"), string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("green"))
        self.highlight_rules.append((QRegExp(r"#.*"), comment_format))

    def highlightBlock(self, text):
        """Applies highlighting to a block of text."""
        for pattern, fmt in self.highlight_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length)

        # Ensure multi-line strings are handled later
        self.setCurrentBlockState(0)

def apply_dark_theme(app):
    """Applies a dark theme to the application."""
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)

    app.setPalette(dark_palette)
    app.setStyle("Fusion")

if __name__ == "__main__":
    import ctypes
    # Set Windows App User Model ID (Important for Taskbar Icon!)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("pi3.postprocess.v1")

    app = QApplication([])
    #apply_dark_theme(app)

    # Load the .bmp file into a QIcon
    icon_path = "c:\src\postprocess\icons8-analyse-60.ico"
    icon = QIcon(icon_path)

    ## Set the application-wide taskbar icon
    app.setWindowIcon(icon)
    
    if os.path.isfile("root_folder.txt"):
        fi=open("root_folder.txt","r")
        lines=fi.readlines()
        fi.close()
        root=lines[0]
    else:
        root=""
    window = FitApp(root)
    #window.setWindowIcon(icon)
    window.show()
    app.exec_()