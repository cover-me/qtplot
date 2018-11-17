import matplotlib as mpl
import matplotlib.pyplot as plt
import textwrap

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QT
from PyQt4 import QtGui, QtCore

from .util import FixedOrderFormatter
import os
import io

class ExportWidget(QtGui.QWidget):
    def __init__(self, main):
        QtGui.QWidget.__init__(self)

        # Set some matplotlib font settings
        mpl.rcParams['mathtext.fontset'] = 'custom'
        mpl.rcParams['mathtext.rm'] = 'Bitstream Vera Sans'
        mpl.rcParams['mathtext.it'] = 'Bitstream Vera Sans:italic'
        mpl.rcParams['mathtext.bf'] = 'Bitstream Vera Sans:bold'

        self.main = main

        self.fig, self.ax = plt.subplots()
        self.filenames = []
        self.cb = None

        self.init_ui()

    def init_ui(self):
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        hbox = QtGui.QHBoxLayout()

        self.b_update = QtGui.QPushButton('Update', self)
        self.b_update.clicked.connect(self.on_update)
        hbox.addWidget(self.b_update)

        self.b_copy = QtGui.QPushButton('To clipboard', self)
        self.b_copy.clicked.connect(self.on_copy)
        hbox.addWidget(self.b_copy)

        self.b_to_ppt = QtGui.QPushButton('To PPT (Win)', self)
        self.b_to_ppt.clicked.connect(self.on_to_ppt)
        hbox.addWidget(self.b_to_ppt)

        self.b_to_word = QtGui.QPushButton('To word (Win)', self)
        self.b_to_word.clicked.connect(self.on_to_word)
        hbox.addWidget(self.b_to_word)

        self.b_export = QtGui.QPushButton('Export...', self)
        self.b_export.clicked.connect(self.on_export)
        hbox.addWidget(self.b_export)
        
        grid_general = QtGui.QGridLayout()

        grid_general.addWidget(QtGui.QLabel('Title'), 1, 1)
        self.le_title = QtGui.QLineEdit('test')
        grid_general.addWidget(self.le_title, 1, 2)

        grid_general.addWidget(QtGui.QLabel('DPI'), 1, 3)
        self.le_dpi = QtGui.QLineEdit('80')
        self.le_dpi.setMaximumWidth(50)
        grid_general.addWidget(self.le_dpi, 1, 4)

        grid_general.addWidget(QtGui.QLabel('Rasterize'), 1, 5)
        self.cb_rasterize = QtGui.QCheckBox('')
        grid_general.addWidget(self.cb_rasterize, 1, 6)

        grid_general.addWidget(QtGui.QLabel('Hold'), 1, 7)
        self.cb_hold = QtGui.QCheckBox('')
        grid_general.addWidget(self.cb_hold, 1, 8)
        self.cb_hold.setCheckState(QtCore.Qt.Unchecked)

        grid = QtGui.QGridLayout()

        # X-axis
        grid.addWidget(QtGui.QLabel('X Label'), 2, 1)
        self.le_x_label = QtGui.QLineEdit('test')
        grid.addWidget(self.le_x_label, 2, 2)

        grid.addWidget(QtGui.QLabel('X Format'), 2, 3)
        self.le_x_format = QtGui.QLineEdit('%.0f')
        self.le_x_format.setMaximumWidth(50)
        grid.addWidget(self.le_x_format, 2, 4)

        grid.addWidget(QtGui.QLabel('X Div'), 2, 5)
        self.le_x_div = QtGui.QLineEdit('1e0')
        self.le_x_div.setMaximumWidth(50)
        grid.addWidget(self.le_x_div, 2, 6)

        # Y-axis
        grid.addWidget(QtGui.QLabel('Y Label'), 3, 1)
        self.le_y_label = QtGui.QLineEdit('test')
        grid.addWidget(self.le_y_label, 3, 2)

        grid.addWidget(QtGui.QLabel('Y Format'), 3, 3)
        self.le_y_format = QtGui.QLineEdit('%.0f')
        self.le_y_format.setMaximumWidth(50)
        grid.addWidget(self.le_y_format, 3, 4)

        grid.addWidget(QtGui.QLabel('Y Div'), 3, 5)
        self.le_y_div = QtGui.QLineEdit('1e0')
        self.le_y_div.setMaximumWidth(50)
        grid.addWidget(self.le_y_div, 3, 6)

        # Z-axis
        grid.addWidget(QtGui.QLabel('Z Label'), 4, 1)
        self.le_z_label = QtGui.QLineEdit('test')
        grid.addWidget(self.le_z_label, 4, 2)

        grid.addWidget(QtGui.QLabel('Z Format'), 4, 3)
        self.le_z_format = QtGui.QLineEdit('%.0f')
        self.le_z_format.setMaximumWidth(50)
        grid.addWidget(self.le_z_format, 4, 4)

        grid.addWidget(QtGui.QLabel('Z Div'), 4, 5)
        self.le_z_div = QtGui.QLineEdit('1e0')
        self.le_z_div.setMaximumWidth(50)
        grid.addWidget(self.le_z_div, 4, 6)

        grid2 = QtGui.QGridLayout()

        # Font
        grid2.addWidget(QtGui.QLabel('Font'), 5, 1)
        self.le_font = QtGui.QLineEdit('Vera Sans')
        grid2.addWidget(self.le_font, 5, 2)

        grid2.addWidget(QtGui.QLabel('Font size'), 6, 1)
        self.le_font_size = QtGui.QLineEdit('12')
        grid2.addWidget(self.le_font_size, 6, 2)

        # Figure size
        grid2.addWidget(QtGui.QLabel('Width'), 5, 3)
        self.le_width = QtGui.QLineEdit('3')
        grid2.addWidget(self.le_width, 5, 4)

        grid2.addWidget(QtGui.QLabel('Height'), 6, 3)
        self.le_height = QtGui.QLineEdit('3')
        grid2.addWidget(self.le_height, 6, 4)

        # Colorbar
        grid2.addWidget(QtGui.QLabel('CB Orient'), 5, 5)
        self.cb_cb_orient = QtGui.QComboBox()
        self.cb_cb_orient.addItems(['vertical', 'horizontal'])
        grid2.addWidget(self.cb_cb_orient, 5, 6)

        grid2.addWidget(QtGui.QLabel('CB Pos'), 6, 5)
        self.le_cb_pos = QtGui.QLineEdit('0 0 1 1')
        grid2.addWidget(self.le_cb_pos, 6, 6)

        # Additional things to plot
        grid2.addWidget(QtGui.QLabel('Triangulation'), 7, 1)
        self.cb_triangulation = QtGui.QCheckBox('')
        grid2.addWidget(self.cb_triangulation, 7, 2)

        grid2.addWidget(QtGui.QLabel('Tripcolor'), 7, 3)
        self.cb_tripcolor = QtGui.QCheckBox('')
        grid2.addWidget(self.cb_tripcolor, 7, 4)

        grid2.addWidget(QtGui.QLabel('Linecut'), 7, 5)
        self.cb_linecut = QtGui.QCheckBox('')
        grid2.addWidget(self.cb_linecut, 7, 6)
              
        # Advance tools
        hbox_av = QtGui.QHBoxLayout()
        
        lb_cmd = QtGui.QLabel('Cmd')
        lb_cmd.setMaximumWidth(20)
        hbox_av.addWidget(lb_cmd)
        
        self.cb_cmd =  QtGui.QComboBox()
        self.cb_cmd.setEditable(True)
        self.cb_cmd.addItem("")
        self.cb_cmd.addItem("plt.plot([0,1],[0,0],'yellow',linewidth=2);self.canvas.draw()")
        self.cb_cmd.addItem("plt.gca().lines[-1].remove();self.canvas.draw()")
        self.cb_cmd.addItem("plt.autoscale(True, 'both', tight=None);self.canvas.draw()")
        self.cb_cmd.addItem("plt.gca().set_xlim(None, None);self.canvas.draw()")
        self.cb_cmd.addItem("plt.tight_layout();self.canvas.draw()")
        self.cb_cmd.addItem("plt.subplots_adjust(0.125,0.1,0.9,0.9);self.canvas.draw()")
        self.cb_cmd.addItem("self.le_ans.setText('%s %s'%(self.main.width(),self.main.height()))")
        self.cb_cmd.addItem("self.main.resize(500,700)")

        hbox_av.addWidget(self.cb_cmd)        

        self.b_run = QtGui.QPushButton('Run', self)
        self.b_run.setMaximumWidth(60)
        self.b_run.clicked.connect(self.on_run)
        hbox_av.addWidget(self.b_run)
        
        self.le_ans = QtGui.QLineEdit(self)
        self.le_ans.setEnabled(False)
        self.le_ans.setMaximumWidth(60)
        hbox_av.addWidget(self.le_ans)
        
        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.toolbar)
        vbox.addWidget(self.canvas)
        vbox.addLayout(hbox)
        vbox.addLayout(grid_general)
        vbox.addLayout(grid)
        vbox.addLayout(grid2)
        vbox.addLayout(hbox_av)

    def populate_ui(self):
        profile = self.main.profile_settings
        
        if '<keep>' not in str(self.le_title.text()):
            self.le_title.setText(profile['title'])
        self.le_dpi.setText(profile['DPI'])
        self.cb_rasterize.setChecked(bool(profile['rasterize']))
        
        self.le_x_label.setText(profile['x_label'])
        self.le_y_label.setText(profile['y_label'])
        self.le_z_label.setText(profile['z_label'])

        self.le_x_format.setText(profile['x_format'])
        self.le_y_format.setText(profile['y_format'])
        self.le_z_format.setText(profile['z_format'])

        self.le_x_div.setText(profile['x_div'])
        self.le_y_div.setText(profile['y_div'])
        self.le_z_div.setText(profile['z_div'])

        self.le_font.setText(profile['font'])
        self.le_width.setText(profile['width'])
        # cb orient

        self.le_font_size.setText(profile['font_size'])
        self.le_height.setText(profile['height'])
        # cb pos

        self.cb_triangulation.setChecked(bool(profile['triangulation']))
        self.cb_tripcolor.setChecked(bool(profile['tripcolor']))
        self.cb_linecut.setChecked(bool(profile['linecut']))

    def keyPressEvent(self, e):#seems not work....
        if e.key() == QtCore.Qt.Key_Return:
            self.on_update()
        elif e.key=='Left':
            self.main.canvas.loadNext(self.parent.abs_filename,-1)
        elif e.key=='Right':
            self.main.canvas.loadNext(self.parent.abs_filename)

    def format_label(self, s):
        conversions = {
            '<filename>': self.main.name,
            '<operations>': self.main.operations.op_str,
            '<x>': self.main.x_name,
            '<y>': self.main.y_name,
            '<z>': self.main.data_name,
            '<keep>':'',
            '<return>':'\n'
        }
        for old, new in conversions.items():
            s = s.replace(old, new)
        for key, item in self.main.dat_file.qtlab_settings.items():
            if isinstance(item, dict):
                for key_, item_ in item.items():
                    s = s.replace('<%s:%s>'%(key,key_), '%s'%item_)
        return s

    def on_update(self):
        """ Draw the entire plot """
        if self.main.data is not None:
            font = {
                'family': str(self.le_font.text()),
                'size': int(str(self.le_font_size.text()))
            }

            mpl.rc('font', **font)

            # Clear the plot
            if self.cb_hold.checkState() == QtCore.Qt.Unchecked:
                self.filenames = []
                self.ax.clear()
            self.filenames.append(os.path.splitext(self.format_label('<filename>'))[0])
            # Get the data and colormap
            x, y, z = self.main.data.get_pcolor()
            cmap = self.main.canvas.colormap.get_mpl_colormap()

            tri_checkboxes = [self.cb_tripcolor.checkState(),
                              self.cb_triangulation.checkState()]

            # If we are going to need to plot triangulation data, prepare
            # the data so it can be plotted
            if QtCore.Qt.Checked in tri_checkboxes:
                if self.main.data.tri is None:
                    self.main.data.generate_triangulation()

                xc, yc = self.main.data.get_triangulation_coordinates()

                tri = mpl.tri.Triangulation(xc, yc,
                                            self.main.data.tri.simplices)

            # Plot the data using either pcolormesh or tripcolor
            if self.cb_tripcolor.checkState() != QtCore.Qt.Checked:
                quadmesh = self.ax.pcolormesh(x, y, z,
                                              cmap=cmap,
                                              rasterized=True)

                quadmesh.set_clim(self.main.canvas.colormap.get_limits())
            else:
                quadmesh = self.ax.tripcolor(tri,
                                             self.main.data.z.ravel(),
                                             cmap=cmap, rasterized=True)

                quadmesh.set_clim(self.main.canvas.colormap.get_limits())

            # Plot the triangulation
            if self.cb_triangulation.checkState() == QtCore.Qt.Checked:
                self.ax.triplot(tri, 'o-', color='black',
                                linewidth=0.5, markersize=3)

            self.ax.axis('tight')

            title = self.format_label(str(self.le_title.text()))
            title += '' if len(self.filenames)<2 else  (' & ' + ' '.join(self.filenames[:-1]))
            title = '\n'.join(textwrap.wrap(title, max(int(30*(self.main.width()/300.)),40), replace_whitespace=False))
            # Set all the plot labels
            self.ax.set_title(title,fontsize=int(str(self.le_font_size.text())))
            self.ax.set_xlabel(self.format_label(self.le_x_label.text()))
            self.ax.set_ylabel(self.format_label(self.le_y_label.text()))

            # Set the axis tick formatters
            self.ax.xaxis.set_major_formatter(FixedOrderFormatter(
                str(self.le_x_format.text()), float(self.le_x_div.text())))
            self.ax.yaxis.set_major_formatter(FixedOrderFormatter(
                str(self.le_y_format.text()), float(self.le_y_div.text())))

            if self.cb is not None:
                self.cb.remove()

            # Colorbar layout
            orientation = str(self.cb_cb_orient.currentText())
            self.cb = self.fig.colorbar(quadmesh, orientation=orientation)

            self.cb.formatter = FixedOrderFormatter(
                str(self.le_z_format.text()), float(self.le_z_div.text()))

            self.cb.update_ticks()

            self.cb.set_label(self.format_label(self.le_z_label.text()))
            self.cb.draw_all()

            # Plot the current linecut if neccesary
            if self.cb_linecut.checkState() == QtCore.Qt.Checked:
                for linetrace in self.main.linecut.linetraces:
                    if linetrace.type == 'horizontal':
                        plt.axhline(linetrace.position, color='red')
                    elif linetrace.type == 'vertical':
                        plt.axvline(linetrace.position, color='red')

            self.fig.tight_layout()

            self.canvas.draw()

    def on_copy(self):
        """ Copy the current plot to the clipboard """
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
        self.on_copy()

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
        self.on_copy()

        # Get the current word file and paste the plot
        worddoc = app.ActiveDocument
        cend = worddoc.Content.End
        worddoc.Range(cend-1,cend).Paste()
        worddoc.Content.InsertAfter('\n')
        app.WindowState=0 #normal the window size. Now it comes back to the front

    def on_export(self):
        """ Export the current plot to a file """
        path = os.path.dirname(os.path.realpath(__file__))

        filters = ('Portable Network Graphics (*.png);;'
                   'Portable Document Format (*.pdf);;'
                   'Postscript (*.ps);;'
                   'Encapsulated Postscript (*.eps);;'
                   'Scalable Vector Graphics (*.svg)')

        filename = QtGui.QFileDialog.getSaveFileName(self,
                                                     caption='Export figure',
                                                     directory=path,
                                                     filter=filters)
        filename = str(filename)

        if filename != '':
            previous_size = self.fig.get_size_inches()
            self.fig.set_size_inches(float(self.le_width.text()),
                                     float(self.le_height.text()))

            dpi = int(self.le_dpi.text())

            self.fig.savefig(filename, dpi=dpi, bbox_inches='tight')
            self.fig.set_size_inches(previous_size)

            self.canvas.draw()
    def on_run(self):
        cmdstr = str(self.cb_cmd.currentText())
        if cmdstr.startswith("plt.") or cmdstr.startswith('self'):
            try:
                exec(cmdstr)
            except:
                self.le_ans.setText('Error!')
