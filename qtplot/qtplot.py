from __future__ import print_function

from six.moves import configparser
import numpy as np
import os
import logging
import sys
from collections import OrderedDict
from PyQt4 import QtGui, QtCore
from .colormap import Colormap
from .data import DatFile, Data2D
from .export import ExportWidget
from .linecut import Linecut
from .operations import Operations
from .settings import Settings
from .canvas import Canvas
from .server import qpServer
from time import time

logger = logging.getLogger(__name__)

PROFILE_DEFAULTS = OrderedDict((
    ('operations', ''),
    ('sub_series_V', ''),
    ('sub_series_I', ''),
    ('sub_series_R', ''),
    ('open_directory', ''),
    ('save_directory', ''),
    ('x', ''),
    ('y', ''),
    ('z', ''),
    ('a3', ''),
    ('a3index', '0'),
    ('colormap', 'transform\\Seismic.npy'),
    ('min','-1'),
    ('max','1'),
    ('gamma','0'),
    ('auto_color',True),
    ('title', '<filename> <operations>'),
    ('DPI', '80,80,300'),
    ('rasterize', True),
    ('hold', False),
    ('x_label', '<x>, <x_dir>'),
    ('y_label', '<y>, <y_dir>'),
    ('z_label', '<z>'),
    ('x_format', '%%f'),
    ('y_format', '%%f'),
    ('z_format', '%%f'),
    ('x_div', '1e0'),
    ('y_div', '1e0'),
    ('z_div', '1e0'),
    ('font', 'DejaVu Sans'),
    ('font_size', '12'),
    ('width', '3'),
    ('height', '3'),
    ('cb_orient', 'vertical'),
    ('cb_pos', '0 0 1 1'),
    ('triangulation', False),
    ('tripcolor', False),
    ('linecut', False),
    ('auto_reset_line', True),
    ('incremental', False),
    ('legend', True),
    ('offset', '0'),
    ('line_style', 'solid'),
    ('line_width', '0.5'),
    ('marker_style', 'None'),
    ('marker_size', '6'),
    ('incl_z', True)
))


class QTPlot(QtGui.QMainWindow):
    """ The main window of the qtplot application. """

    def __init__(self, filename=None):
        super(QTPlot, self).__init__(None)
        self.settings_dir = os.path.join(os.path.expanduser('~'), '.qtplot')
        self.is_first_data_file = True
        self.name = None
        self.closed = False
        self.filename = None
        self.abs_filename = None
        self.max_load_time = 0
        self.data = None
        
        self.init_logging()

        self.dat_file = DatFile(self)
        self.linecut = Linecut(self)
        self.operations = Operations(self)
        self.settings = Settings(self)
        self.qpServer = qpServer(self)
        
        self.init_settings()
        self.init_ui()
        self.settings.populate_ui()

        if filename is not None:
            self.load_dat_file(filename)
            
    def init_settings(self):
        # settings_dir/qtplot.ini: {'default_profile': 'default.ini'}
        # settings_dir/profiles/default.ini: PROFILE_DEFAULTS
        # profile_settings: {'default_profile': 'default.ini'}
        self.profiles_dir = os.path.join(self.settings_dir, 'profiles')
        self.operations_dir = os.path.join(self.settings_dir, 'operations')

        # Create the program directories if they don't exist yet
        for dir in [self.settings_dir, self.profiles_dir, self.operations_dir]:
            if not os.path.exists(dir):
                os.makedirs(dir)

        self.qtplot_ini_file = os.path.join(self.settings_dir, 'qtplot.ini')

        defaults = {'default_profile': 'default.ini'}
        self.profile_settings = defaults
        self.qtplot_ini = configparser.SafeConfigParser(defaults)#initialize qtplot_ini
        self.profile_ini = configparser.SafeConfigParser(PROFILE_DEFAULTS)#initialize profile_ini

        # If a qtplot.ini exists: read it to qtplot_ini
        # Else: save the qtplot_ini as file qtplot.ini
        if os.path.exists(self.qtplot_ini_file):
            self.qtplot_ini.read(self.qtplot_ini_file)
        else:
            with open(self.qtplot_ini_file, 'w') as config_file:
                self.qtplot_ini.write(config_file)

        default_profile = self.qtplot_ini.get('DEFAULT', 'default_profile')#get filename
        self.profile_ini_file = os.path.join(self.profiles_dir, default_profile)

        # if the default profile ini doesn't exist, write defaults to a file
        # if exist, will read it later
        if not os.path.isfile(self.profile_ini_file):
            with open(self.profile_ini_file, 'w') as config_file:
                self.profile_ini.write(config_file)



    def init_logging(self):
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.WARNING)
        if not os.path.exists(self.settings_dir):
            os.makedirs(self.settings_dir)
        log_file = os.path.join(self.settings_dir, 'log.txt')
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Write exceptions to the log
        def my_handler(exc_type, exc_value, exc_traceback):
            exc_info = (exc_type, exc_value, exc_traceback)
            logger.error('Uncaught exception', exc_info=exc_info)

        sys.excepthook = my_handler

    def init_ui(self):
        self.setWindowTitle('qtplot')

        self.main_widget = QtGui.QTabWidget(self)

        self.view_widget = QtGui.QWidget()
        self.main_widget.addTab(self.view_widget, 'View')
        self.export_widget = ExportWidget(self)
        self.main_widget.addTab(self.export_widget, 'Export')

        self.canvas = Canvas(self)
        
        # path
        hbox = QtGui.QHBoxLayout()
        
        lbl_folder = QtGui.QLabel('Path:')
        hbox.addWidget(lbl_folder)
        
        self.le_path = QtGui.QLineEdit(self)
        self.le_path.returnPressed.connect(self.on_refresh)
        hbox.addWidget(self.le_path)
        
        # Top row buttons
        hbox2 = QtGui.QHBoxLayout()
        
        self.b_load = QtGui.QPushButton('Load..')
        self.b_load.clicked.connect(self.on_load_dat)
        hbox.addWidget(self.b_load)

        self.b_refresh = QtGui.QPushButton('Refresh')
        self.b_refresh.clicked.connect(self.on_refresh)
        hbox.addWidget(self.b_refresh)
        
        self.b_swap_axes = QtGui.QPushButton('Swap XY', self)
        self.b_swap_axes.clicked.connect(self.on_swap_axes)
        hbox2.addWidget(self.b_swap_axes)

        self.b_linecut = QtGui.QPushButton('Linecut')
        self.b_linecut.clicked.connect(self.linecut.show_window)
        hbox2.addWidget(self.b_linecut)

        self.b_operations = QtGui.QPushButton('Operations')
        self.b_operations.clicked.connect(self.operations.show_window)
        hbox2.addWidget(self.b_operations)

        # Subtracting series R
        r_hbox = QtGui.QHBoxLayout()
        
        lbl_v = QtGui.QLabel('V-I-R:')
        r_hbox.addWidget(lbl_v)

        self.cb_v = QtGui.QComboBox(self)
        self.cb_v.setMaxVisibleItems(25)
        self.cb_v.setMinimumContentsLength(3)
        self.cb_v.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed))
        r_hbox.addWidget(self.cb_v)

        self.cb_i = QtGui.QComboBox(self)
        self.cb_i.setMaxVisibleItems(25)
        self.cb_i.setMinimumContentsLength(3)
        self.cb_i.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed))
        r_hbox.addWidget(self.cb_i)

        self.le_r = QtGui.QLineEdit(self)
        self.le_r.returnPressed.connect(self.on_sub_series_r)
        self.le_r.setMaximumWidth(30)
        r_hbox.addWidget(self.le_r)

        self.b_ok = QtGui.QPushButton('Sub', self)
        self.b_ok.setToolTip('Subtract series R')
        self.b_ok.setMaximumWidth(30)
        self.b_ok.clicked.connect(self.on_sub_series_r)
        r_hbox.addWidget(self.b_ok)
        
        lbl_a3 = QtGui.QLabel('A3:')
        r_hbox.addWidget(lbl_a3)

        self.cb_a3 = QtGui.QComboBox(self)
        self.cb_a3.setToolTip('The 3rd axis')
        self.cb_a3.setMinimumContentsLength(3)
        # self.cb_a3.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed))
        r_hbox.addWidget(self.cb_a3)
        
        self.le_a3index = QtGui.QLineEdit(self)
        self.le_a3index.setText('0')
        self.le_a3index.setToolTip('Index')
        self.le_a3index.setMaximumWidth(15)
        self.le_a3index.setValidator(QtGui.QIntValidator(0,0))
        self.le_a3index.returnPressed.connect(self.on_refresh)
        r_hbox.addWidget(self.le_a3index)

 

        # Selecting columns and orders
        grid = QtGui.QGridLayout()

        lbl_x = QtGui.QLabel("X:", self)
        lbl_x.setMaximumWidth(10)
        grid.addWidget(lbl_x, 1, 1)

        self.cb_x = QtGui.QComboBox(self)
        self.cb_x.activated.connect(self.on_data_change)
        self.cb_x.setMaxVisibleItems(25)
        grid.addWidget(self.cb_x, 1, 2)

        lbl_y = QtGui.QLabel("Y:", self)
        grid.addWidget(lbl_y, 2, 1)

        self.cb_y = QtGui.QComboBox(self)
        self.cb_y.activated.connect(self.on_data_change)
        self.cb_y.setMaxVisibleItems(25)
        grid.addWidget(self.cb_y, 2, 2)

        lbl_d = QtGui.QLabel("Data:", self)
        grid.addWidget(lbl_d, 3, 1)

        self.cb_z = QtGui.QComboBox(self)
        self.cb_z.activated.connect(self.on_data_change)
        self.cb_z.setMaxVisibleItems(25)
        grid.addWidget(self.cb_z, 3, 2)

        self.combo_boxes = [self.cb_v, self.cb_i,
                            self.cb_x, self.cb_y, self.cb_z, self.cb_a3]

        # Colormap
        hbox_gamma1 = QtGui.QHBoxLayout()
        hbox_gamma2 = QtGui.QHBoxLayout()
        hbox_gamma3 = QtGui.QHBoxLayout()
        
        # Reset colormap button
        self.cb_reset_cmap = QtGui.QCheckBox('Auto reset')
        self.cb_reset_cmap.setCheckState(QtCore.Qt.Checked)
        hbox_gamma1.addWidget(self.cb_reset_cmap)

        # Colormap combobox
        self.cb_cmaps = QtGui.QComboBox(self)
        self.cb_cmaps.setMinimumContentsLength(5)
        self.cb_cmaps.activated.connect(self.on_cmap_change)
        path = os.path.dirname(os.path.realpath(__file__))

        path = os.path.join(path, 'colormaps')

        cmap_files = []
        for dir, _, files in os.walk(path):
            for filename in files:
                reldir = os.path.relpath(dir, path)
                relfile = os.path.join(reldir, filename)

                # Remove .\ for files in the root of the directory
                if relfile[:2] == '.\\':
                    relfile = relfile[2:]

                cmap_files.append(relfile)

        self.cb_cmaps.addItems(cmap_files)
        self.cb_cmaps.setMaxVisibleItems(25)

        hbox_gamma1.addWidget(self.cb_cmaps)

        # Colormap minimum text box
        hbox_gamma2.addWidget(QtGui.QLabel('Min:'))
        self.le_min = QtGui.QLineEdit(self)
        # self.le_min.setMaximumWidth(80)
        self.le_min.returnPressed.connect(self.on_min_max_entered)
        hbox_gamma2.addWidget(self.le_min)

        # Colormap minimum slider
        self.s_min = QtGui.QSlider(QtCore.Qt.Horizontal)
        # self.s_min.setMaximum(100)
        self.s_min.sliderMoved.connect(self.on_min_changed)
        hbox_gamma3.addWidget(self.s_min)

        # Gamma text box
        hbox_gamma2.addWidget(QtGui.QLabel('G:'))
        self.le_gamma = QtGui.QLineEdit(self)
        # self.le_gamma.setMaximumWidth(80)
        self.le_gamma.returnPressed.connect(self.on_le_gamma_entered)
        hbox_gamma2.addWidget(self.le_gamma)
        
        # Colormap gamma slider
        self.s_gamma = QtGui.QSlider(QtCore.Qt.Horizontal)
        self.s_gamma.setMinimum(-100)
        # self.s_gamma.setMaximum(100)
        self.s_gamma.setValue(0)
        self.s_gamma.valueChanged.connect(self.on_gamma_changed)
        hbox_gamma3.addWidget(self.s_gamma)

        # Colormap maximum text box
        hbox_gamma2.addWidget(QtGui.QLabel('Max:'))
        self.le_max = QtGui.QLineEdit(self)
        # self.le_max.setMaximumWidth(80)
        self.le_max.returnPressed.connect(self.on_min_max_entered)
        hbox_gamma2.addWidget(self.le_max)

        # Colormap maximum slider
        self.s_max = QtGui.QSlider(QtCore.Qt.Horizontal)
        # self.s_max.setMaximum(100)
        self.s_max.setValue(self.s_max.maximum())
        self.s_max.sliderMoved.connect(self.on_max_changed)
        hbox_gamma3.addWidget(self.s_max)


        self.b_reset = QtGui.QPushButton('Reset')
        self.b_reset.setMinimumWidth(50)
        self.b_reset.clicked.connect(self.on_cm_reset)
        hbox_gamma1.addWidget(self.b_reset)

        # Bottom row buttons
        self.b_settings = QtGui.QPushButton('Settings')
        self.b_settings.clicked.connect(self.settings.show_window)
        hbox2.addWidget(self.b_settings)

        self.b_save_matrix = QtGui.QPushButton('Save data')
        self.b_save_matrix.clicked.connect(self.on_save_matrix)
        hbox2.addWidget(self.b_save_matrix)

        for i in range(hbox2.count()):
            w = hbox2.itemAt(i).widget()
            if isinstance(w, QtGui.QPushButton):
                w.setMinimumWidth(50)

        # Main box
        vbox = QtGui.QVBoxLayout(self.view_widget)
        vbox.addWidget(self.canvas.native)
        vbox2 = QtGui.QVBoxLayout()   
        vbox2.addLayout(hbox)
        vbox2.addLayout(hbox2)
        vbox2.addLayout(r_hbox)
        vbox2.addLayout(grid)
        vbox2.addLayout(hbox_gamma1)
        vbox2.addLayout(hbox_gamma2)
        vbox2.addLayout(hbox_gamma3)
        s_widget = QtGui.QWidget() 
        s_widget.setLayout(vbox2)
        s_area = QtGui.QScrollArea()
        s_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        s_area.setFixedHeight(s_widget.sizeHint().height())
        s_area.setFrameStyle(QtGui.QScrollArea.NoFrame)
        s_area.setWidgetResizable(True)
        s_area.setWidget(s_widget)
        vbox.addWidget(s_area)
        
        self.status_bar = QtGui.QStatusBar()
        self.l_position = QtGui.QLabel('(x, y)')
        self.l_position.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse|QtCore.Qt.TextSelectableByKeyboard)
        self.status_bar.addWidget(self.l_position,1)
        
        self.l_linepos = QtGui.QLabel('')
        self.l_linepos.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse|QtCore.Qt.TextSelectableByKeyboard)
        self.l_linepos.setToolTip('Linecut position. [x1,y1],[x2,y2] or so')
        self.status_bar.addWidget(self.l_linepos)
        
        self.l_slope = QtGui.QLabel('k')
        self.l_slope.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse|QtCore.Qt.TextSelectableByKeyboard)
        self.l_slope.setToolTip('Linecut slope')
        self.status_bar.addWidget(self.l_slope)
        self.load_time = QtGui.QLabel('t (t_max)')
        self.load_time.setToolTip('Loading time (max loading time) in ms')
        self.status_bar.addWidget(self.load_time)     
        self.status_bar.setMinimumWidth(50)
        self.setStatusBar(self.status_bar)

        self.main_widget.setFocus()
        self.setCentralWidget(self.main_widget)
        
        self.setAcceptDrops(True)
        
        self.resize(500, 800)
        self.move(200, 100)
        self.show()
        self.linecut.resize(520, 400)
        self.linecut.move(self.width()+220, 100)
        self.operations.resize(400, 200)
        self.operations.move(self.width()+220, 540)
        self.linecut.show()
        self.operations.show()
        
    def update_ui(self, changeValue=False):
        """
        repopulate combo_boxes ['sub_series_V', 'sub_series_I', 'x', 'y', 'z', 'a3']
        if changeValue=True, restore profile values to combo_boxes, R, cmap, gamma, a3index...
        """
        if self.name is not None:
            self.setWindowTitle(self.name)
            parameters = [''] + self.get_parameter_names()
            # Repopulate the combo boxes and keep the indexes
            for cb in self.combo_boxes:
                i = cb.currentIndex()
                cb.clear()
                if cb is self.cb_a3:
                    cb.addItems(parameters[:4])
                else:
                    cb.addItems(parameters)
                cb.setCurrentIndex(i)
                    
            if changeValue:
                # set R
                self.le_r.setText(self.profile_settings['sub_series_R'])
                # set ['sub_series_V', 'sub_series_I', 'x', 'y', 'z', 'a3']
                names = ['sub_series_V', 'sub_series_I', 'x', 'y', 'z', 'a3']
                for i, cb in enumerate(self.combo_boxes):
                    parameter = self.profile_settings[names[i]]
                    index = cb.findText(parameter)
                    if index == -1:
                        logger.error('update_ui: Could not find the indice: %s'%parameter)
                    else:
                        cb.setCurrentIndex(index)
                # Set the colormap
                cmap = self.profile_settings['colormap']
                cmap = cmap.replace('\\', '/') if os.path.sep == '/' else cmap.replace('/', '\\')
                index = self.cb_cmaps.findText(cmap)
                if index != -1:
                    self.cb_cmaps.setCurrentIndex(index)
                else:
                    logger.error('update_ui: Could not find the colormap file %s' % cmap)
                #min max gamma...
                try:#these value are not saved before 2018-12
                    self.cb_reset_cmap.setCheckState(QtCore.Qt.Unchecked)#self.profile_settings['auto_color']*2) or use self.cb_rasterize.setChecked
                    self.le_min.setText(self.profile_settings['min'])
                    self.le_max.setText(self.profile_settings['max'])
                    self.le_a3index.setText(self.profile_settings['a3index'])
                    self.on_min_max_entered(update_canvas=False)#min max edit line entered
                    self.on_gamma_changed(float(self.profile_settings['gamma']),update_canvas=False)#gamma slider changed
                except Exception as e:
                    logger.warning('update_ui: Could not update min, max, gamma: %s'%e)
                    
            if self.is_first_data_file:
                self.cb_reset_cmap.setChecked(self.profile_settings['auto_color'])
                default_indices = [0, 0, 1, 2, 4, 0]#['sub_series_V', 'sub_series_I', 'x', 'y', 'z', 'a3']
                for cb, i in zip(self.combo_boxes, default_indices):
                    cb.setCurrentIndex(i)
                self.is_first_data_file = False   
            
        else:
            logger.info('update_ui: file name is None, nothing updated')

    def load_dat_file(self, filename):
        """
        Load a .dat/.npy/.mtx file, it's .set file if present, update the GUI elements,
        and fire an on_data_change event to update the plots.
        """
        t0 = time()
        is_new_filename = self.dat_file.update_file(filename)
        if is_new_filename:
            self.settings.fill_tree()
            path, self.name = os.path.split(filename)
            self.filename = filename
            self.abs_filename = os.path.abspath(filename)
            self.open_state(self.profile_ini_file,changeValue=self.is_first_data_file)
        else:
            self.on_data_change()
        t2 = time()
        ld_time = (t2-t0)*1000
        self.max_load_time = max(self.max_load_time,ld_time)
        self.load_time.setText('%d (%d) ms'%(ld_time,self.max_load_time))
        
    def update_parameters(self):
        pass

    def save_default_profile(self, file):
        self.qtplot_ini.set('DEFAULT', 'default_profile', file)

        with open(self.qtplot_ini_file, 'w') as config_file:
            self.qtplot_ini.write(config_file)

    def save_state(self, filename):
        """
        Save the current qtplot state into a .ini file and the operations
        in a corresponding .json file.
        """
        profile_name = os.path.splitext(os.path.basename(filename))[0]

        operations_file = os.path.join(self.operations_dir,
                                       profile_name + '.json')

        self.operations.save(operations_file)
        operations_file2 = os.path.basename(operations_file) if self.operations_dir == self.profiles_dir else operations_file
        state = OrderedDict((
            ('operations', operations_file2),
            ('sub_series_V', str(self.cb_v.currentText())),
            ('sub_series_I', str(self.cb_i.currentText())),
            ('sub_series_R', str(self.le_r.text())),
            ('open_directory', self.profile_settings['open_directory']),
            ('save_directory', self.profile_settings['save_directory']),
            ('x', str(self.cb_x.currentText())),
            ('y', str(self.cb_y.currentText())),
            ('z', str(self.cb_z.currentText())),
            ('colormap', str(self.cb_cmaps.currentText())),
            ('min',str(self.le_min.text())),
            ('max',str(self.le_max.text())),
            ('gamma',str(self.le_gamma.text())),
            ('auto_color',self.cb_reset_cmap.isChecked()),
            ('title', str(self.export_widget.le_title.text())),
            ('DPI', str(self.export_widget.le_dpi.text())),
            ('rasterize', self.export_widget.cb_rasterize.isChecked()),
            ('hold', self.export_widget.cb_hold.isChecked()),
            ('x_label', str(self.export_widget.le_x_label.text())),
            ('y_label', str(self.export_widget.le_y_label.text())),
            ('z_label', str(self.export_widget.le_z_label.text())),
            ('x_format', str(self.export_widget.le_x_format.text())),
            ('y_format', str(self.export_widget.le_y_format.text())),
            ('z_format', str(self.export_widget.le_z_format.text())),
            ('x_div', str(self.export_widget.le_x_div.text())),
            ('y_div', str(self.export_widget.le_y_div.text())),
            ('z_div', str(self.export_widget.le_z_div.text())),
            ('font', str(self.export_widget.le_font.text())),
            ('font_size', str(self.export_widget.le_font_size.text())),
            ('width', str(self.export_widget.le_width.text())),
            ('height', str(self.export_widget.le_height.text())),
            ('cb_orient', str(self.export_widget.cb_cb_orient.currentText())),
            ('cb_pos', str(self.export_widget.le_cb_pos.text())),
            ('triangulation', self.export_widget.cb_triangulation.isChecked()),
            ('tripcolor', self.export_widget.cb_tripcolor.isChecked()),
            ('linecut', self.export_widget.cb_linecut.isChecked()),
            ('auto_reset_line', self.linecut.cb_reset_cmap.isChecked()),
            ('incremental', self.linecut.cb_incremental.isChecked()),
            ('legend', self.linecut.cb_showLegend.isChecked()),
            ('offset', str(self.linecut.le_offset.text())),
            ('line_style', str(self.linecut.cb_linestyle.currentText())),
            ('line_width', str(self.linecut.le_linewidth.text())),
            ('marker_style', str(self.linecut.cb_markerstyle.currentText())),
            ('marker_size', str(self.linecut.le_markersize.text())),
            ('incl_z', self.linecut.cb_include_z.isChecked())
        ))

        for option, value in state.items():
            # ConfigParser doesn't like single %
            value = str(value).replace('%', '%%')

            self.profile_ini.set('DEFAULT', option, value)

        path = os.path.join(self.profiles_dir, filename)

        with open(path, 'w') as config_file:
            self.profile_ini.write(config_file)

    def open_state(self, filename, changeValue = True):
        """ Load all settings into the GUI """
        # profile_ini_file and operations files
        self.profile_ini_file = os.path.join(self.profiles_dir, filename)
        self.profile_name = os.path.splitext(os.path.basename(filename))[0]
        operations_file = os.path.join(self.operations_dir,
                                       self.profile_name + '.json')
        # Load the operations and the specified profile .ini
        if os.path.exists(operations_file):
            self.operations.load(operations_file)
        else:
            logger.info('No operations file present for selected profile.')
        self.profile_ini.read(self.profile_ini_file)
        
        # Update profile_settings with profile_ini
        for option in PROFILE_DEFAULTS.keys():#option means key
            value = self.profile_ini.get('DEFAULT', option)
            if value in ['False', 'True']:
                value = self.profile_ini.getboolean('DEFAULT', option)
            self.profile_settings[option] = value
        
        # Apply R to sub_series_r
        try:
            R = float(self.profile_settings['sub_series_R'])#ValueError if empty string
            self.sub_series_r(self.profile_settings['sub_series_V'],
                              self.profile_settings['sub_series_I'],
                              R)
        except ValueError:
            logger.info('R is not given.')

        self.update_ui(changeValue)
        self.on_cmap_change(update_canvas=False)# should only update the canvas once
        self.on_data_change()
        
        if changeValue:
            self.export_widget.populate_ui()
            self.linecut.populate_ui()

        # If we are viewing the export tab, update the plot
        if self.main_widget.currentIndex() == 1:
            self.export_widget.on_update()

    def get_parameter_names(self):
        return self.dat_file.ids
    
    def get_a3(self):
        a3 = self.cb_a3.currentIndex()-1
        if a3 not in range(3):
            self.le_a3index.setText('0')
            a3 = 2
            a3index = 0
        else:
            a3index = int(self.le_a3index.text())
        a3index_max = self.dat_file.shape[a3]-1
        return a3,a3index,a3index_max

    def on_data_change(self):
        """
        This is called when anything concerning the data has changed. This can
        consist of a new data file being loaded, a change in parameter to plot,
        or a change/addition of an Operation.

        A clean version of the Data2D is retrieved from the DatFile,
        all the operations are applied to the data, and it is plotted.
        """
        self.canvas.clear()
        # Get the selected axes from the interface
        if self.filename is None or not os.path.isfile(self.filename):
            return
        x_name, y_name, data_name = self.get_axis_names()
        # Update the Data2D
        a3,a3index,a3index_max = self.get_a3()
        if a3index > a3index_max:
            a3index = a3index_max
            self.le_a3index.setText('%s'%a3index_max)
        self.le_a3index.setValidator(QtGui.QIntValidator(0,a3index_max))
        # If the dataset is 1D; disable the y-parameter combobox
        if self.dat_file.get_dim() == 0:
            self.cb_x.setCurrentIndex(0)
            self.cb_x.setEnabled(False)
            self.cb_y.setCurrentIndex(0)
            self.cb_y.setEnabled(False)
        elif self.dat_file.get_dim() == 1:
            self.cb_x.setEnabled(True)
            self.cb_y.setCurrentIndex(0)
            self.cb_y.setEnabled(False)
        else:
            self.cb_x.setEnabled(True)
            self.cb_y.setEnabled(True)
        self.data = self.dat_file.get_data(x_name,y_name,data_name,a3,a3index) # return Data2D object
        if self.data is None:
            return
            
        # Apply the selected operations
        self.data = self.operations.apply_operations(self.data)
        

        # If we want to reset the colormap for each data update, do so
        if self.cb_reset_cmap.checkState() == QtCore.Qt.Checked:
            self.on_cm_reset()

        self.canvas.set_data(self.data)
        # Update the linecut
        self.canvas.draw_linecut(None, old_position=True)

        #if np.isnan(self.data.z).any():
            #logger.warning('The data contains NaN values')

    def get_axis_names(self):
        """ Get the parameters that are currently selected to be plotted """
        self.x_name = str(self.cb_x.currentText())
        self.y_name = str(self.cb_y.currentText())
        self.data_name = str(self.cb_z.currentText())

        return self.x_name, self.y_name, self.data_name

    def on_load_dat(self, event):
        open_directory = self.profile_settings['open_directory']
        filename = str(QtGui.QFileDialog.getOpenFileName(directory=open_directory,
                                                         filter='*.dat;;*.npy'))
        self.le_path.setText(filename)
        if filename != "":
            self.load_dat_file(filename)

    def on_refresh(self):
        new_filepath = str(self.le_path.text()).strip()
        if os.path.isfile(new_filepath) and any([new_filepath.endswith(x) for x in ['.dat','.npy','.mtx']]):
            self.filename = new_filepath
            self.load_dat_file(self.filename)
        else:
            self.le_path.setText("Error file path!")

    def on_swap_axes(self, event):
        x, y = self.cb_x.currentIndex(), self.cb_y.currentIndex()
        self.cb_x.setCurrentIndex(y)
        self.cb_y.setCurrentIndex(x)
        self.on_data_change()

    def sub_series_r(self, V_param, I_param, R):
        if self.dat_file is None:
            return

        if (V_param in self.dat_file.ids and I_param in self.dat_file.ids):
            voltages = self.dat_file.get_column(V_param)
            currents = self.dat_file.get_column(I_param)
            adjusted = voltages - currents * R

            self.dat_file.set_column(V_param + ' - Sub series R', adjusted)

    def on_sub_series_r(self, event=None):
        V_param = str(self.cb_v.currentText())

        self.sub_series_r(V_param,
                          str(self.cb_i.currentText()),
                          float(self.le_r.text()))

        self.update_ui()

        x_col = str(self.cb_x.currentText())
        y_col = str(self.cb_y.currentText())

        # If the current x/y axis was the voltage axis to be corrected
        # then switch to the corrected values
        if V_param == x_col:
            self.cb_x.setCurrentIndex(self.cb_x.count() - 1)
        elif V_param == y_col:
            self.cb_y.setCurrentIndex(self.cb_y.count() - 1)

        self.on_data_change()

    def on_cmap_change(self, event=None, update_canvas = True):
        selected_cmap = str(self.cb_cmaps.currentText())

        path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(path, 'colormaps', selected_cmap)
        
        if path != self.canvas.colormap.path:
            new_colormap = Colormap(path)
            new_colormap.min = self.canvas.colormap.min
            new_colormap.max = self.canvas.colormap.max
            self.canvas.colormap = new_colormap
            if update_canvas:
                self.canvas.update()

    def on_min_max_entered(self, update_canvas=True):
        if self.data is not None:
            zmin, zmax = np.nanmin(self.data.z), np.nanmax(self.data.z)

            newmin = float(self.le_min.text())
            newmax = float(self.le_max.text())

            # Convert the entered bounds into slider positions (0 - 100)
            self.s_min.setValue((newmin - zmin) / ((zmax - zmin) / 100))
            self.s_max.setValue((newmax - zmin) / ((zmax - zmin) / 100))

            cm = self.canvas.colormap
            cm.min, cm.max = newmin, newmax
            
            if update_canvas:
                self.canvas.update()
    
    def on_min_changed(self, value, update_canvas=True):
        if self.data is not None:
            min, max = np.nanmin(self.data.z), np.nanmax(self.data.z)

            newmin = min + (max - min) * (value / 99.0)
            self.le_min.setText('%.2e' % newmin)

            self.canvas.colormap.min = newmin
            if update_canvas:
                self.canvas.update()

    def on_le_gamma_entered(self):
        newgamma = float(self.le_gamma.text())
        if newgamma != self.s_gamma.value():
            self.s_gamma.setValue(newgamma)
            self.on_gamma_changed(newgamma)

    def on_gamma_changed(self, value, update_canvas=True):
        self.le_gamma.setText('%.1f'% value)
        if self.data is not None:
            gamma = 10.0**(value / 100.0)
            self.canvas.colormap.gamma = gamma
            if update_canvas:
                self.canvas.update()

    def on_max_changed(self, value, update_canvas=True):
        if self.data is not None:
            min, max = np.nanmin(self.data.z), np.nanmax(self.data.z)

            # This stuff with the 99 is hacky, something is going on which
            # causes the highest values not to be rendered using the colormap.
            # The 99 makes the cm max a bit higher than the actual maximum
            newmax = min + (max - min) * (value / 99.0)
            self.le_max.setText('%.2e' % newmax)

            self.canvas.colormap.max = newmax
            if update_canvas:
                self.canvas.update()

    def on_cm_reset(self):
        if self.data is not None:
            self.s_min.setValue(0)
            self.on_min_changed(0, update_canvas=False)
            self.s_gamma.setValue(0)
            self.on_gamma_changed(0, update_canvas=False)
            self.s_max.setValue(100)
            self.on_max_changed(100)

    def on_save_matrix(self):
        save_directory = self.profile_settings['save_directory']

        filters = ('QTLab data format (*.dat);;'
                   'NumPy binary matrix format (*.npy);;'
                   'MATLAB matrix format (*.mat);;'
                   'Spyview matrix format (*.mtx)')

        filename = QtGui.QFileDialog.getSaveFileName(self,
                                                     caption='Save file',
                                                     directory=save_directory,
                                                     filter=filters)
        filename = str(filename)

        if filename != '' and self.dat_file is not None:
            base = os.path.basename(filename)
            name, ext = os.path.splitext(base)

            self.data.save(filename)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = str(event.mimeData().urls()[0].toString())
            if any([url.endswith(x) for x in ['.dat','.npy','.mtx']]) or (url.endswith('.ini') and self.name==os.path.basename(url)[:-4]):
                event.accept()

    def dropEvent(self, event):
        filepath = str(event.mimeData().urls()[0].toLocalFile())
        if filepath.endswith('.ini'):
            old1 = self.operations_dir
            old2 = self.profiles_dir
            self.operations_dir = os.path.split(filepath)[0]
            self.profiles_dir = self.operations_dir
            self.open_state(os.path.basename(filepath),changeValue=True)
            self.operations_dir = old1
            self.profiles_dir = old2
        else:
            self.le_path.setText(filepath)
            self.load_dat_file(filepath)
            
    def moveEvent(self, event):
        super(QTPlot, self).moveEvent(event)
        diff = event.pos() - event.oldPos()
        for i in [self.linecut,self.operations,self.settings]:
            geo = i.geometry()
            geo.moveTopLeft(geo.topLeft() + diff)
            i.setGeometry(geo)

    def resizeEvent(self, event):
        super(QTPlot, self).resizeEvent(event)
        diff = event.size() - event.oldSize()
        diff = QtCore.QPoint(diff.width(),0)
        for i in [self.linecut,self.operations,self.settings]:
            geo = i.geometry()
            geo.moveTopLeft(geo.topLeft() + diff)
            i.setGeometry(geo)

    def closeEvent(self, event):
        self.linecut.close()
        self.operations.close()
        self.settings.close()
        self.qpServer.deleteLater()
        del self.dat_file.data # data may be a mmap
        self.closed = True



def main():
    app = QtGui.QApplication(sys.argv)
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        QTPlot(filename=sys.argv[1])
    else:
        QTPlot()
    sys.exit(app.exec_())
