import matplotlib.pyplot as plt
import numpy as np
import os
import io
import pandas as pd
import textwrap
from itertools import cycle

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT

from PyQt4 import QtGui, QtCore

from .util import FixedOrderFormatter, eng_format


class Linetrace(plt.Line2D):
    """
    Represents a linetrace from the data. The purpose of this class is
    to be able to store incremental linetraces in an array.

    x/y:        Arrays containing x and y data
    type:       Type of linetrace, 'horizontal' or 'vertical'
    traceLabel:   label containing infomation of the file name and the x/y coordinate at which the linetrace was taken
    """

    def __init__(self, x, y, row_numbers, type, position, traceLabel, **kwargs):
        plt.Line2D.__init__(self, x, y, label=traceLabel,  **kwargs)

        self.row_numbers = row_numbers
        self.type = type
        self.traceLabel = traceLabel
        self.position = position
class LineColors():
    def __init__(self,c_list):
        self.c_list = c_list
        self.index = 0
    def get_next(self):
        self.index += 1
        if self.index == len(self.c_list):
            self.index = 0
        return self.c_list[self.index]
    def dec_index(self):
        self.index -= 1
        if self.index == -1:
            self.index = len(self.c_list) - 1
    def set_index(self,i):
        self.index = i

class Linecut(QtGui.QDialog):
    def __init__(self, main=None):
        super(Linecut, self).__init__(main)
        
        self.main = main

        self.fig, self.ax = plt.subplots()
        self.x, self.y = None, None
        self.linetraces = []
        self.marker = None
        self.colors = LineColors('rbgcmyk')
        self.singleLine = True

        self.ax.xaxis.set_major_formatter(FixedOrderFormatter())
        self.ax.yaxis.set_major_formatter(FixedOrderFormatter())

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Linecut")

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.mpl_connect('pick_event', self.on_pick)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        hbox_export = QtGui.QHBoxLayout()

        self.cb_reset_cmap = QtGui.QCheckBox('Auto reset')
        self.cb_reset_cmap.setCheckState(QtCore.Qt.Checked)
        hbox_export.addWidget(self.cb_reset_cmap)

        self.b_copy = QtGui.QPushButton('Copy', self)
        self.b_copy.clicked.connect(self.on_figure_to_clipboard)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+C"),
                        self, self.on_figure_to_clipboard)
        hbox_export.addWidget(self.b_copy)

        self.b_to_ppt = QtGui.QPushButton('To PPT', self)
        self.b_to_ppt.clicked.connect(self.on_to_ppt)
        hbox_export.addWidget(self.b_to_ppt)
        
        self.b_to_word = QtGui.QPushButton('To Word', self)
        self.b_to_word.clicked.connect(self.on_to_word)
        hbox_export.addWidget(self.b_to_word)

        self.b_save = QtGui.QPushButton('Copy data', self)
        self.b_save.clicked.connect(self.on_data_to_clipboard)
        hbox_export.addWidget(self.b_save)

        self.b_save_dat = QtGui.QPushButton('Save data', self)
        self.b_save_dat.clicked.connect(self.on_save)
        hbox_export.addWidget(self.b_save_dat)

        self.b_toggle_info = QtGui.QPushButton('Toggle info')
        self.b_toggle_info.clicked.connect(self.on_toggle_datapoint_info)
        hbox_export.addWidget(self.b_toggle_info)

        # Linecuts
        hbox_linecuts = QtGui.QHBoxLayout()

        hbox_linecuts.addWidget(QtGui.QLabel('Linecuts'))

        self.cb_incremental = QtGui.QCheckBox('Incremental')
        self.cb_incremental.setCheckState(QtCore.Qt.Unchecked)
        hbox_linecuts.addWidget(self.cb_incremental)
        
        self.cb_showLegend = QtGui.QCheckBox('Legend')
        self.cb_showLegend.setCheckState(QtCore.Qt.Checked)
        hbox_linecuts.addWidget(self.cb_showLegend)

        hbox_linecuts.addWidget(QtGui.QLabel('Offset:'))

        self.le_offset = QtGui.QLineEdit('0', self)
        hbox_linecuts.addWidget(self.le_offset)

        self.b_clear_lines = QtGui.QPushButton('Clear', self)
        self.b_clear_lines.clicked.connect(self.on_clear_lines)
        hbox_linecuts.addWidget(self.b_clear_lines)

        # Lines
        hbox_style = QtGui.QHBoxLayout()

        hbox_style.addWidget(QtGui.QLabel('Line'))
        self.cb_linestyle = QtGui.QComboBox(self)
        self.cb_linestyle.addItems(['None', 'solid', 'dashed', 'dotted'])
        hbox_style.addWidget(self.cb_linestyle)

        hbox_style.addWidget(QtGui.QLabel('Linewidth'))
        self.le_linewidth = QtGui.QLineEdit('0.5', self)
        hbox_style.addWidget(self.le_linewidth)

        # Markers
        hbox_style.addWidget(QtGui.QLabel('Marker'))
        self.cb_markerstyle = QtGui.QComboBox(self)
        self.cb_markerstyle.addItems(['None', '.', 'o', 'x'])
        hbox_style.addWidget(self.cb_markerstyle)

        hbox_style.addWidget(QtGui.QLabel('Size'))
        self.le_markersize = QtGui.QLineEdit('0.5', self)
        hbox_style.addWidget(self.le_markersize)

        self.cb_include_z = QtGui.QCheckBox('Include Z')
        self.cb_include_z.setCheckState(QtCore.Qt.Checked)
        hbox_style.addWidget(self.cb_include_z)

        self.row_tree = QtGui.QTreeWidget(self)
        self.row_tree.setHeaderLabels(['Parameter', 'Value'])
        self.row_tree.setColumnWidth(0, 100)
        self.row_tree.setHidden(True)

        hbox_plot = QtGui.QHBoxLayout()
        hbox_plot.addWidget(self.canvas)
        hbox_plot.addWidget(self.row_tree)
        
        for i in range(hbox_export.count()):
            w = hbox_export.itemAt(i).widget()
            if isinstance(w, QtGui.QPushButton):
                w.setMinimumWidth(20)
                
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addLayout(hbox_plot)
        layout.addLayout(hbox_export)
        layout.addLayout(hbox_linecuts)
        layout.addLayout(hbox_style)
        self.setLayout(layout)

    def populate_ui(self):
        profile = self.main.profile_settings

        idx = self.cb_linestyle.findText(profile['line_style'])
        self.cb_linestyle.setCurrentIndex(idx)
        self.le_linewidth.setText(profile['line_width'])

        idx = self.cb_markerstyle.findText(profile['marker_style'])
        self.cb_markerstyle.setCurrentIndex(idx)
        self.le_markersize.setText(profile['marker_size'])

    def get_line_kwargs(self):
        return {
            'linestyle': str(self.cb_linestyle.currentText()),
            'linewidth': float(self.le_linewidth.text()),
            'marker': str(self.cb_markerstyle.currentText()),
            'markersize': float(self.le_markersize.text()),
        }

    def on_reset(self):
        if self.x is not None and self.y is not None:
            minx, maxx = np.min(self.x), np.max(self.x)
            miny, maxy = np.min(self.y), np.max(self.y)

            xdiff = (maxx - minx) * .1
            ydiff = (maxy - miny) * .1

            self.ax.axis([minx - xdiff, maxx + xdiff,
                          miny - ydiff, maxy + ydiff])

            self.canvas.draw()

    def on_pick(self, event):
        if event.mouseevent.button == 1:
            line = self.linetraces[0]

            ind = event.ind[int(len(event.ind) / 2)]
            x = line.get_xdata()[ind]
            y = line.get_ydata()[ind]

            row = int(line.row_numbers[ind])
            data = self.main.dat_file.get_row_info(row)

            # Also show the datapoint index
            data['N'] = ind

            # Fill the treeview with data
            self.row_tree.clear()
            widgets = []
            for name, value in data.items():
                if name == 'N':
                    val = str(value)
                else:
                    val = eng_format(value, 1)

                widgets.append(QtGui.QTreeWidgetItem(None, [name, val]))

            self.row_tree.insertTopLevelItems(0, widgets)

            # Remove the previous datapoint marker
            if self.marker is not None:
                self.marker.remove()
                self.marker = None

            # Plot a new datapoint marker
            self.marker = self.ax.plot(x, y, '.',
                                       markersize=15,
                                       color='black')[0]

        self.fig.canvas.draw()

    def on_press(self, event):
        if event.button == 3:
            self.row_tree.clear()

            if self.marker is not None:
                self.marker.remove()
                self.marker = None

            self.fig.canvas.draw()

    def on_toggle_datapoint_info(self):
        self.row_tree.setHidden(not self.row_tree.isHidden())

    def on_data_to_clipboard(self):
        if self.x is None or self.y is None:
            return

        data = pd.DataFrame(np.column_stack((self.x, self.y)),
                            columns=[self.xlabel, self.ylabel])

        data.to_clipboard(index=False)

    def on_figure_to_clipboard(self):
        buf = io.BytesIO()
        self.fig.savefig(buf)
        img = QtGui.QImage.fromData(buf.getvalue())
        QtGui.QApplication.clipboard().setImage(img)
        buf.close()

    def on_to_ppt(self):
        """ Some win32 COM magic to interact with powerpoint """
        try:
            import win32com.client
            app = win32com.client.GetActiveObject('PowerPoint.Application')
            app.WindowState=2 #minimize the window so it will come back to the front later
        except ImportError:
            print('ERROR: win32com library missing or no ppt file opened')
            return

        # First, copy to the clipboard
        self.on_figure_to_clipboard()

        # Get the current slide and paste the plot
        slide = app.ActiveWindow.View.Slide
        shape = slide.Shapes.Paste()

        # Add a hyperlink to the data location to easily open the data again
        if self.main.abs_filename:
            shape.ActionSettings[0].Hyperlink.Address = self.main.abs_filename
        app.WindowState=1 #normal the window size. Now it comes back to the front

    def on_to_word(self):
        """ Some win32 COM magic to interact with word """
        try:
            import win32com.client
            # Connect to an open word application
            app = win32com.client.GetActiveObject('word.application')
            app.WindowState=2 #minimize the window so it will come back to the front later
        except:
            print('ERROR: win32com library missing or no word file opened')
            return

        # copy to the clipboard
        self.on_figure_to_clipboard()

        # Get the current word file and paste the plot
        worddoc = app.ActiveDocument
        cend = worddoc.Content.End
        worddoc.Range(cend-1,cend).Paste()
        worddoc.Content.InsertAfter('\n')
        app.WindowState=0 #normal the window size. Now it comes back to the front

    def on_save(self):
        if self.x is None or self.y is None:
            return

        path = os.path.dirname(os.path.realpath(__file__))
        filename = QtGui.QFileDialog.getSaveFileName(self,
                                                     'Save file',
                                                     path,
                                                     '.dat')

        if filename != '':
            data = pd.DataFrame(np.column_stack((self.x, self.y)),
                                columns=[self.xlabel, self.ylabel])

            data.to_csv(filename, sep='\t', index=False)

    def on_clear_lines(self):
        for line in self.linetraces:
            line.remove()
        _ = self.ax.legend_
        if _:
            _.remove()
        self.singleLine = True

        self.linetraces = []

        self.fig.canvas.draw()

    def plot_linetrace(self, x, y, z, row_numbers, type, position, title,
                       xlabel, ylabel, otherlabel):
        # Don't draw lines consisting of one point
        if np.count_nonzero(~np.isnan(y)) < 2:
            return

        self.xlabel, self.ylabel, self.otherlabel = xlabel, ylabel, otherlabel
        self.title = title
        self.x, self.y, self.z = x, y, z

        if self.cb_include_z.checkState() == QtCore.Qt.Checked:
            title = '{0} {1}={2}'.format(title, otherlabel, z) if (otherlabel or z!='0') else title

        title = '\n'.join(textwrap.wrap(title, 60, replace_whitespace=False))
        self.ax.set_title(title,fontsize=int(str(self.main.export_widget.le_font_size.text())))

        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)
        traceLabel = self.main.name.replace('.dat',' ')
        traceLabel += z if (otherlabel or z!='0') else ''

        # Remove all the existing lines and only plot one if we uncheck
        # the incremental box. Else, add a new line to the collection
        if self.cb_incremental.checkState() == QtCore.Qt.Unchecked:
            if self.singleLine == False:
                self.ax.legend_.remove()
                self.singleLine = True
            for line in self.linetraces:
                line.remove()

            self.linetraces = []

            line = Linetrace(x, y, row_numbers, type, position, traceLabel,
                             color='red',
                             picker=5,
                             **self.get_line_kwargs())

            self.linetraces.append(line)
            self.ax.add_line(line)

            self.total_offset = 0
        else:
            if self.singleLine:
                self.colors.set_index(0 if len(self.ax.lines) == 1 else -1)
                self.singleLine = False
            if len(self.ax.lines) > 0:
                if self.linetraces[-1].traceLabel == traceLabel or self.linetraces[-1].traceLabel.split()[0].endswith('.npy'):
                    self.linetraces[-1].remove()
                    del self.linetraces[-1]
                    self.colors.dec_index()

            index = len(self.linetraces) - 1

            offset = float(self.le_offset.text())
            line = Linetrace(x, y + index * offset, row_numbers, type, position, traceLabel,
                                color = self.colors.get_next(),
                                **self.get_line_kwargs())
            self.linetraces.append(line)
            x1,x2 = self.ax.get_xlim()
            y1,y2 = self.ax.get_ylim()
            self.ax.add_line(line)
            if self.cb_showLegend.checkState()== QtCore.Qt.Checked:
                self.ax.legend(loc=0)
            else:
                self.ax.legend().set_visible(False)

        if self.cb_reset_cmap.checkState() == QtCore.Qt.Checked:
            x, y = np.ma.masked_invalid(x), np.ma.masked_invalid(y)
            minx, maxx = np.min(x), np.max(x)
            miny, maxy = np.min(y), np.max(y)

            xdiff = (maxx - minx) * .05
            ydiff = (maxy - miny) * .05
            
            if  self.cb_incremental.checkState() == QtCore.Qt.Checked and len(self.ax.lines) > 1:
                self.ax.axis([min(minx - xdiff,x1), max(maxx + xdiff,x2), min(miny - ydiff,y1), max(maxy + ydiff,y2)])
            else:
                self.ax.axis([minx - xdiff, maxx + xdiff, miny - ydiff, maxy + ydiff])

        self.ax.set_aspect('auto')
        self.fig.tight_layout()

        self.fig.canvas.draw()

    def resizeEvent(self, event):
        self.fig.tight_layout()
        self.canvas.draw()

    def show_window(self):
        if self.isHidden():
            self.show()
            self.raise_()
        else:
            self.hide()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
