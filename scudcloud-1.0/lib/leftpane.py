from PyQt4 import QtCore
from PyQt4.QtCore import QUrl
from PyQt4.QtWebKit import QWebView, QWebSettings

from resources import Resources


class LeftPane(QWebView):

    def __init__(self, window):
        QWebView.__init__(self)
        self.window = window
        with open(Resources.get_path('leftpane.js'), 'r') as f:
            self.js = f.read()
        self.setFixedWidth(0)
        self.setVisible(False)
        # We don't want plugins for this simple pane
        self.settings().setAttribute(QWebSettings.PluginsEnabled, False)
        self.setUrl(QUrl().fromLocalFile(Resources.get_path('leftpane.html')))
        self.page().currentFrame().addToJavaScriptWindowObject('leftPane', self)
        self.page().currentFrame().evaluateJavaScript(self.js)

    def show(self):
        self.setFixedWidth(65)
        self.setVisible(True)

    def hide(self):
        self.setFixedWidth(0)
        self.setVisible(False)

    def addTeam(self, tid, name, url, icon, active=False):
        if active is True:
            checked = 'true'
        else:
            checked = 'false'
        self.page().currentFrame().evaluateJavaScript(
            "LeftPane.addTeam('{}','{}','{}','{}','{}');".format(tid, name, url, icon, checked)
        )

    def click(self, i):
        self.page().currentFrame().evaluateJavaScript("LeftPane.click({});".format(i))

    def alert(self, team):
        if team is not None:
            self.page().currentFrame().evaluateJavaScript("LeftPane.alert('{}');".format(team))

    def stopAlert(self, team):
        if team is not None:
            self.page().currentFrame().evaluateJavaScript("LeftPane.stopAlert('{}');".format(team))

    @QtCore.pyqtSlot(str)
    def switchTo(self, url):
        self.window.switch_to(url)

    def contextMenuEvent(self, event):
        pass


