from PyQt4 import QtCore, QtNetwork
import os
import logging

logger = logging.getLogger(__name__)

class qpServer(QtCore.QObject):
    def __init__(self, main, port=1787):
        logger.info('Initialize tcp server at port %s...'%port)
        super(qpServer, self).__init__()
        self.main = main
        self.tcpServer = QtNetwork.QTcpServer(self)
        if not self.tcpServer.listen(QtNetwork.QHostAddress.LocalHost, port):
            logger.warning("Unable to start the server: %s." % self.tcpServer.errorString())
            return
        self.tcpServer.newConnection.connect(self.on_new_connection)
    def on_new_connection(self):
        self.client = self.tcpServer.nextPendingConnection()
        self.client.readyRead.connect(self.on_ready_read)
        self.client.disconnected.connect(self.client.deleteLater)
    def on_ready_read(self):
        msg = self.client.readAll().data()
        if msg != '':
            msg_return = self.handle_remote_msg(msg)
            if msg_return:
                self.client.write(msg_return)
        self.client.disconnectFromHost()
    def handle_remote_msg(self,msg):
        cmd = msg.split(';')
        msg_return = ''
        for i in cmd:
            try:
                key,value = i.split(':',1)
                if key == 'FILE':
                    if os.path.isfile(value):
                        self.main.le_path.setText(value)
                        self.main.main_widget.setCurrentIndex(0)
                        self.main.load_dat_file(value)
                        msg_return += 'FILE:Done!;'
                    else:
                        msg_return += 'FILE:Error file path;'
                elif key == 'AXES':
                    try:
                        x_ind,y_ind,z_ind = map(int,value.split(','))
                    except:
                        msg_return += 'AXES:Index error;'
                    self.main.cb_x.setCurrentIndex(x_ind)
                    self.main.cb_y.setCurrentIndex(y_ind)
                    self.main.cb_z.setCurrentIndex(z_ind)
                    self.main.on_data_change()
                    msg_return += 'AXES:Done!;'
                elif key == 'SHOW':
                    self.main.showMinimized()
                    self.main.activateWindow()
                    self.main.showNormal()
                    msg_return += 'SHOW:Done!;'
                elif key == 'REFR':
                    if self.main.filename == value:
                        self.main.load_dat_file(value)
                elif key == 'UPDA':
                    if self.main.filename == value:
                        self.main.export_widget.on_update()
                        msg_return += 'UPDA:Done!;'
                    else:
                        msg_return += 'UPDA:Error file path;'
                else:
                    msg_return += 'Unknown key:%s;'%key
            except:
                msg_return +=  'Unknown msg:%s;'%i
        msg_return = 'qtplot:'+msg_return if msg_return != '' else ''
        return msg_return
