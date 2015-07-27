#!/usr/bin/env python3
import os

from PyQt4 import QtCore, QtGui, QtWebKit
from PyQt4.Qt import QKeySequence
from PyQt4.QtCore import QSettings
from PyQt4.QtWebKit import QWebSettings

from cookiejar import PersistentCookieJar
from leftpane import LeftPane
from notifier import Notifier
from resources import Resources
from systray import Systray
from wrapper import Wrapper


# Auto-detection of Unity and Dbusmenu in gi repository
try:
    from gi.repository import Unity, Dbusmenu
except ImportError:
    Unity = None
    Dbusmenu = None
    from launcher import DummyLauncher


class ScudCloud(QtGui.QMainWindow):
    plugins = True
    debug = False
    forceClose = False
    messages = 0

    def __init__(self, parent=None, settings_path=''):
        super(ScudCloud, self).__init__(parent)
        self.setWindowTitle('ScudCloud')
        self.settings_path = settings_path
        self.notifier = Notifier(Resources.APP_NAME, Resources.get_path('scudcloud.png'))
        self.settings = QSettings(os.path.join(self.settings_path, 'scudcloud.cfg'), QSettings.IniFormat)
        self.identifier = self.settings.value('Domain')
        if Unity is not None:
            self.launcher = Unity.LauncherEntry.get_for_desktop_id('scudcloud.desktop')
        else:
            self.launcher = DummyLauncher(self)
        self.cookiesjar = None
        self.zoom = 1
        self.web_settings()
        self.leftPane = LeftPane(self)
        web_view = Wrapper(self)
        web_view.page().networkAccessManager().setCookieJar(self.cookiesjar)
        self.stackedWidget = QtGui.QStackedWidget()
        self.stackedWidget.addWidget(web_view)
        central_widget = QtGui.QWidget(self)
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.leftPane)
        layout.addWidget(self.stackedWidget)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.addMenu()
        self.tray = Systray(self)
        self.toggle_close_to_tray()
        self.toggle_show_tray(ScudCloud.minimized)
        self.installEventFilter(self)
        if self.identifier is None:
            web_view.load(QtCore.QUrl(Resources.SIGNIN_URL))
        else:
            web_view.load(QtCore.QUrl(self.domain()))
        web_view.show()

    def web_settings(self):
        self.cookiesjar = PersistentCookieJar(self)
        self.zoom = self.read_zoom()
        # Required by Youtube videos (HTML5 video support only on Qt5)
        QWebSettings.globalSettings().setAttribute(QWebSettings.PluginsEnabled, self.plugins)
        # We don't want Java
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavaEnabled, False)
        # We don't need History
        QWebSettings.globalSettings().setAttribute(QWebSettings.PrivateBrowsingEnabled, True)
        # Required for copy and paste clipboard integration
        QWebSettings.globalSettings().setAttribute(QWebSettings.JavascriptCanAccessClipboard, True)
        # Enabling Inspeclet only when --debug=True (requires more CPU usage)
        QWebSettings.globalSettings().setAttribute(QWebSettings.DeveloperExtrasEnabled, self.debug)

    def toggle_full_screen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def restore(self):
        geometry = self.settings.value('geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
        window_state = self.settings.value('windowState')
        if window_state is not None:
            self.restoreState(window_state)
        else:
            self.showMaximized()

    def is_systray_shown(self):
        return self.settings.value('Systray') == 'True'

    def toggle_close_to_tray(self, show=None):
        if show is None:
            show = self.settings.value('SystrayClose') == 'True'
        if show:
            self.menus['file']['close'].setEnabled(True)
            self.settings.setValue('SystrayClose', 'True')
        else:
            self.menus['file']['close'].setEnabled(False)
            self.settings.setValue('SystrayClose', 'False')

    def toggle_show_tray(self, show=None):
        if show is None:
            show = self.is_systray_shown()
        if show:
            self.settings.setValue('Systray', 'True')
            self.tray.show()
        else:
            self.settings.setValue('Systray', 'False')
            self.tray.hide()

    def read_zoom(self):
        default = 1
        if self.settings.value('Zoom') is not None:
            default = float(self.settings.value('Zoom'))
        return default

    def set_zoom(self, factor=1.):
        if factor > 0:
            for i in range(0, self.stackedWidget.count()):
                widget = self.stackedWidget.widget(i)
                widget.setZoomFactor(factor)
            self.settings.setValue('Zoom', factor)

    def zoom_in(self):
        self.set_zoom(self.current().zoomFactor() + 0.1)

    def zoom_out(self):
        self.set_zoom(self.current().zoomFactor() - 0.1)

    def zoom_reset(self):
        self.set_zoom()

    def addMenu(self):
        self.menus = {
            'file': {
                'preferences': self.create_action('Preferences', lambda : self.current().preferences()),
                'systray': self.create_action('Always Show Tray Icon', self.toggle_show_tray, None, True),
                'systray_close': self.create_action('Close to Tray', self.toggle_close_to_tray, None, True),
                'addTeam': self.create_action('Sign in to Another Team', lambda : self.current().addTeam()),
                'signout': self.create_action('Signout', self.current().logout),
                'close': self.create_action('Close', self.close, QKeySequence.Close),
                'exit': self.create_action('Quit', self.exit, QKeySequence.Quit)
            },
            'edit': {
                'undo': self.current().pageAction(QtWebKit.QWebPage.Undo),
                'redo': self.current().pageAction(QtWebKit.QWebPage.Redo),
                'cut': self.current().pageAction(QtWebKit.QWebPage.Cut),
                'copy': self.current().pageAction(QtWebKit.QWebPage.Copy),
                'paste': self.current().pageAction(QtWebKit.QWebPage.Paste),
                'back': self.current().pageAction(QtWebKit.QWebPage.Back),
                'forward': self.current().pageAction(QtWebKit.QWebPage.Forward),
                'reload': self.current().pageAction(QtWebKit.QWebPage.Reload)
            },
            'view': {
                'zoomin': self.create_action('Zoom In', self.zoom_in, QKeySequence.ZoomIn),
                'zoomout': self.create_action('Zoom Out', self.zoom_out, QKeySequence.ZoomOut),
                'reset': self.create_action('Reset', self.zoom_reset, QtCore.Qt.CTRL + QtCore.Qt.Key_0),
                'fullscreen': self.create_action('Toggle Full Screen', self.toggle_full_screen, QtCore.Qt.Key_F11)
            },
            'help': {
                'help': self.create_action('Help and Feedback', self.current().help, QKeySequence.HelpContents),
                'center': self.create_action('Slack Help Center', self.current().helpCenter),
                'about': self.create_action('About', lambda : self.current().about())
            }
        }
        menu = self.menuBar()
        file_menu = menu.addMenu('&File')
        file_menu.addAction(self.menus['file']['preferences'])
        file_menu.addSeparator()
        file_menu.addAction(self.menus['file']['systray'])
        file_menu.addAction(self.menus['file']['systray_close'])
        file_menu.addSeparator()
        file_menu.addAction(self.menus['file']['addTeam'])
        file_menu.addAction(self.menus['file']['signout'])
        file_menu.addSeparator()
        file_menu.addAction(self.menus['file']['close'])
        file_menu.addAction(self.menus['file']['exit'])
        edit_menu = menu.addMenu('&Edit')
        edit_menu.addAction(self.menus['edit']['undo'])
        edit_menu.addAction(self.menus['edit']['redo'])
        edit_menu.addSeparator()
        edit_menu.addAction(self.menus['edit']['cut'])
        edit_menu.addAction(self.menus['edit']['copy'])
        edit_menu.addAction(self.menus['edit']['paste'])
        edit_menu.addSeparator()
        edit_menu.addAction(self.menus['edit']['back'])
        edit_menu.addAction(self.menus['edit']['forward'])
        edit_menu.addAction(self.menus['edit']['reload'])
        view_menu = menu.addMenu('&View')
        view_menu.addAction(self.menus['view']['zoomin'])
        view_menu.addAction(self.menus['view']['zoomout'])
        view_menu.addAction(self.menus['view']['reset'])
        view_menu.addSeparator()
        view_menu.addAction(self.menus['view']['fullscreen'])
        help_menu = menu.addMenu('&Help')
        help_menu.addAction(self.menus['help']['help'])
        help_menu.addAction(self.menus['help']['center'])
        help_menu.addSeparator()
        help_menu.addAction(self.menus['help']['about'])
        self.enable_menus(False)
        systray_close = self.settings.value('SystrayClose') == 'True'
        self.menus['file']['systray_close'].setChecked(systray_close)
        self.menus['file']['close'].setEnabled(systray_close)
        show_systray = self.is_systray_shown()
        self.menus['file']['systray'].setChecked(show_systray)

    def enable_menus(self, enabled):
        self.menus['file']['preferences'].setEnabled(bool(enabled))
        self.menus['file']['addTeam'].setEnabled(bool(enabled))
        self.menus['file']['signout'].setEnabled(bool(enabled))
        self.menus['help']['help'].setEnabled(bool(enabled))

    def create_action(self, text, slot, shortcut=None, checkable=False):
        action = QtGui.QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        if checkable:
            action.setCheckable(True)
        return action

    def domain(self):
        if self.identifier.endswith('.slack.com'):
            return self.identifier
        else:
            return 'https://{}.slack.com'.format(self.identifier)

    def current(self):
        return self.stackedWidget.currentWidget()

    def teams(self, teams):
        if teams is not None and len(teams) > 1:
            self.leftPane.show()
            for t in teams:
                try:
                    self.leftPane.addTeam(
                        t['id'], t['team_name'], t['team_url'], t['team_icon']['image_88'], t == teams[0]
                    )
                except:
                    self.leftPane.addTeam(t['id'], t['team_name'], t['team_url'], '', t == teams[0])

    def switch_to(self, url):
        q_url = QtCore.QUrl(url)
        index = -1
        for i in range(0, self.stackedWidget.count()):
            if self.stackedWidget.widget(i).url().toString().startswith(url):
                index = i
                break
        if index != -1:
            self.stackedWidget.setCurrentIndex(index)
        else:
            web_view = Wrapper(self)
            web_view.page().networkAccessManager().setCookieJar(self.cookiesjar)
            web_view.load(q_url)
            web_view.show()
            self.stackedWidget.addWidget(web_view)
            self.stackedWidget.setCurrentWidget(web_view)
        self.quicklist(self.current().listChannels())
        self.enable_menus(self.current().isConnected())
        # Save the last used team as default
        self.settings.setValue('Domain', 'https://{}'.format(q_url.host()))

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.ActivationChange and self.isActiveWindow():
            self.focusInEvent(event)
        if event.type() == QtCore.QEvent.KeyPress:
            # Ctrl + <n>
            if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
                if event.key() == QtCore.Qt.Key_1:
                    self.leftPane.click(0)
                elif event.key() == QtCore.Qt.Key_2:
                    self.leftPane.click(1)
                elif event.key() == QtCore.Qt.Key_3:
                    self.leftPane.click(2)
                elif event.key() == QtCore.Qt.Key_4:
                    self.leftPane.click(3)
                elif event.key() == QtCore.Qt.Key_5:
                    self.leftPane.click(4)
                elif event.key() == QtCore.Qt.Key_6:
                    self.leftPane.click(5)
                elif event.key() == QtCore.Qt.Key_7:
                    self.leftPane.click(6)
                elif event.key() == QtCore.Qt.Key_8:
                    self.leftPane.click(7)
                elif event.key() == QtCore.Qt.Key_9:
                    self.leftPane.click(8)
            # Ctrl + Shift + <key>
            if (QtGui.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier) and (
                QtGui.QApplication.keyboardModifiers() & QtCore.Qt.ShiftModifier
            ):
                if event.key() == QtCore.Qt.Key_V:
                    self.current().createSnippet()
        return QtGui.QMainWindow.eventFilter(self, obj, event)

    def focusInEvent(self, event):
        self.count()
        self.launcher.set_property('urgent', False)
        self.tray.stopAlert()

    def title_changed(self):
        self.setWindowTitle(self.current().title())

    def closeEvent(self, event):
        if not self.forceClose and self.settings.value('SystrayClose') == 'True':
            self.hide()
            self.tray.show()
            event.ignore()
        else:
            self.cookiesjar.save()
            self.settings.setValue('geometry', self.saveGeometry())
            self.settings.setValue('windowState', self.saveState())

    def show(self):
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.activateWindow()
        self.setVisible(True)

    def exit(self):
        self.forceClose = True
        self.close()

    def quicklist(self, channels):
        if Dbusmenu is not None:
            ql = Dbusmenu.Menuitem.new()
            self.launcher.set_property('quicklist', ql)
            if channels is not None:
                for c in channels:
                    if c['is_member']:
                        item = Dbusmenu.Menuitem.new()
                        item.property_set(Dbusmenu.MENUITEM_PROP_LABEL, '#{}'.format(c['name']))
                        item.property_set('id', c['name'])
                        item.property_set_bool(Dbusmenu.MENUITEM_PROP_VISIBLE, True)
                        item.connect(Dbusmenu.MENUITEM_SIGNAL_ITEM_ACTIVATED, self.current().openChannel)
                        ql.child_append(item)
                self.launcher.set_property('quicklist', ql)

    def notify(self, title, message):
        self.notifier.notify(title, message)
        self.alert()

    def alert(self):
        if not self.isActiveWindow():
            self.launcher.set_property('urgent', True)
            self.tray.alert()

    def count(self):
        total = 0
        for i in range(0, self.stackedWidget.count()):
            widget = self.stackedWidget.widget(i)
            if widget.messages == 0:
                self.leftPane.stopAlert(widget.team())
            else:
                self.leftPane.alert(widget.team())
            total += widget.messages
        if total > self.messages:
            self.alert()
        if 0 == total:
            self.launcher.set_property('count_visible', False)
            self.tray.set_counter(0)
        else:
            self.tray.set_counter(total)
            self.launcher.set_property('count', total)
            self.launcher.set_property('count_visible', True)
        self.messages = total
