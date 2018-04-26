from PyQt4 import QtCore, QtNetwork
import os
class qpServer(QtCore.QObject):
    def __init__(self, main, port=1787):
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
        self.client.write(self.handle_remote_msg(msg))
        self.client.disconnectFromHost()
    def handle_remote_msg(self,msg):
        try:
            key,value = msg.split(':',1)
        except:
            return 'Unknown msg!'
        if key == 'FILE':
            if os.path.isfile(value) and value.endswith('.dat'):
                self.main.load_dat_file(value)
                return 'FILE:Done!'
            else:
                return 'FILE:Error file path.'
        elif key == 'AXES':
            try:
                x_ind,y_ind,z_ind = map(int,value.split(','))
            except:
                return 'AXES:Index error!'
            self.main.cb_x.setCurrentIndex(x_ind)
            self.main.cb_y.setCurrentIndex(y_ind)
            self.main.cb_z.setCurrentIndex(z_ind)
            self.main.on_data_change()
            return 'AXES:Done!'
        else:
            return 'Unknown key!'