from PyQt4 import QtCore, QtGui

from resources import Resources


class Systray(QtGui.QSystemTrayIcon):
    urgent = False

    def __init__(self, window):
        super(Systray, self).__init__(QtGui.QIcon.fromTheme('scudcloud'), window)
        self.connect(self, QtCore.SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.activated_event)
        self.window = window
        self.setToolTip(Resources.APP_NAME)
        self.menu = QtGui.QMenu(self.window)
        self.menu.addAction('Show/Hide', self.toggle)
        self.menu.addSeparator()
        self.menu.addAction(self.window.menus['file']['preferences'])
        self.menu.addAction(self.window.menus['help']['about'])
        self.menu.addSeparator()
        self.menu.addAction(self.window.menus['file']['exit'])
        self.setContextMenu(self.menu)

    def alert(self):
        if not self.urgent:
            self.urgent = True
            self.setIcon(QtGui.QIcon.fromTheme('scudcloud-attention'))

    def stopAlert(self):
        self.urgent = False
        self.setIcon(QtGui.QIcon.fromTheme('scudcloud'))

    def set_counter(self, i):
        if not i:
            if self.urgent:
                self.setIcon(QtGui.QIcon.fromTheme('scudcloud-attention'))
            else:
                self.setIcon(QtGui.QIcon.fromTheme('scudcloud'))
        elif 0 < i < 10:
            self.setIcon(QtGui.QIcon.fromTheme('scudcloud-attention-{}'.format(i)))
        else:
            self.setIcon(QtGui.QIcon.fromTheme('scudcloud-attention-9-plus'))

    def restore(self):
        self.window.show()
        self.stopAlert()
        if not self.window.is_systray_shown():
            self.hide()

    def toggle(self):
        if self.window.isHidden() or self.window.isMinimized() or not self.window.isActiveWindow():
            self.restore()
        else:
            self.window.hide()

    def activated_event(self, reason):
        if reason in [QtGui.QSystemTrayIcon.MiddleClick, QtGui.QSystemTrayIcon.Trigger]:
            self.toggle()
