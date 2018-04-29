![alt tag](screenshot.png)

## Installation

### Install qtplot with Anaconda Python
Qtplot is compatible with both Python 2 and 3. Using the Anaconda Python distribution (https://www.continuum.io/downloads) is recommended to make installing packages like `numpy` and `scipy` easier.

Create a new environment:

`conda create --name qtplot python=3.5`

Install qtplot:

`pip install qtplot`

Install other dependencies with:

`conda install numpy scipy pandas matplotlib pyqt=4`

Executables will be generated in the `/Scripts` folder of your Python environment with the names `qtplot.<exe>` and `qtplot-console.<exe>`. Associate one of these with `*.dat` files for them to be automatically opened in qtplot.

### Install qtplot with WinPython
WinPython is a free open-source portable distribution of Python.

Download WinPython-32bit-2.7.9.5 installer and run it. The installer only copies files to a destination directory.
 
Open "WinPython Command Prompt.exe" in the destination directory. Type "pip install qtplot".

Find qtplot.exe in folder \python-2.7.9\Scripts.

### Freezes (packages) qtplot with PyInstaller
With PyInstaller, you can package qtplot into a small and portable folder with executables.

Make sure your python meets the requirements of qtplot.

Download the whole project and created a .py file in the project folder, with the following codes:
	
	from qtplot import qtplot
	qtplot.main()

Assuming the file you created names 'qt_plot.py' and WinPython-32bit-2.7.9.5 is used, open "WinPython Command Prompt.exe" and execute:

	cd [directory]
	pyinstaller --hidden-import vispy.app.backends._pyqt4 --add-data qtplot\colormaps;qtplot\colormaps --noconsole qt_plot.py

Replace [directory] with the path of your qtplot project folder.
