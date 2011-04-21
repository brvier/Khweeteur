import sys
from PySide.QtGui import QColor, \
    QMainWindow, \
    QRadialGradient, \
    QToolButton, \
    QFont, \
    QApplication, \
    QPen, \
    QToolBar, \
    QPushButton, \
    QPainterPath, \
    QBrush, \
    QPainter
from PySide.QtCore import Qt

class QBadgeButton (QPushButton):

    def __init__ (self, icon = None, text = None, parent = None):
        if icon:
            QPushButton.__init__(self, icon, text, parent)
        elif text:
            QPushButton.__init__(self, text, parent)
        else:
            QPushButton.__init__(self, parent)

        self.badge_counter = 0
        self.badge_size = 50

        self.redGradient = QRadialGradient(0.0, 0.0, 17.0, self.badge_size - 3, self.badge_size - 3);
        self.redGradient.setColorAt(0.0, QColor(0xe0, 0x84, 0x9b));
        self.redGradient.setColorAt(0.5, QColor(0xe9, 0x34, 0x43));
        self.redGradient.setColorAt(1.0, QColor(0xdc, 0x0c, 0x00));

    def setSize (self, size):
        self.badge_size = size

    def setCounter (self, counter):
        self.badge_counter = counter
        self.update()

    def getCounter (self):
        return self.badge_counter

    def paintEvent (self, event):
        QPushButton.paintEvent(self, event)
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.Antialiasing)

        if self.badge_counter > 0:
            point = self.rect().topRight()
            self.drawBadge(p, point.x()-self.badge_size - 1, point.y() + 1, self.badge_size, str(self.badge_counter), QBrush(self.redGradient))

    def fillEllipse (self, painter, x, y, size, brush):
        path = QPainterPath()
        path.addEllipse(x, y, size, size);
        painter.fillPath(path, brush);

    def drawBadge(self, painter, x, y, size, text, brush):
        painter.setFont(QFont(painter.font().family(), 11, QFont.Bold))

        while ((size - painter.fontMetrics().width(text)) < 10):
            pointSize = painter.font().pointSize() - 1
            weight = QFont.Normal if (pointSize < 8) else QFont.Bold
            painter.setFont(QFont(painter.font().family(), painter.font().pointSize() - 1, weight))

        shadowColor = QColor(0, 0, 0, size)
        self.fillEllipse(painter, x + 1, y, size, shadowColor)
        self.fillEllipse(painter, x - 1, y, size, shadowColor)
        self.fillEllipse(painter, x, y + 1, size, shadowColor)
        self.fillEllipse(painter, x, y - 1, size, shadowColor)

        painter.setPen(QPen(Qt.white, 2));
        self.fillEllipse(painter, x, y, size - 3, brush)
        painter.drawEllipse(x, y, size - 3, size - 3)

        painter.setPen(QPen(Qt.white, 1));
        painter.drawText(x, y, size - 2, size - 2, Qt.AlignCenter, text);

class QToolBadgeButton (QToolButton):

    def __init__ (self, parent = None):
        QToolButton.__init__(self, parent)

        self.badge_counter = 0
        self.badge_size = 25

        self.redGradient = QRadialGradient(0.0, 0.0, 17.0, self.badge_size - 3, self.badge_size - 3);
        self.redGradient.setColorAt(0.0, QColor(0xe0, 0x84, 0x9b));
        self.redGradient.setColorAt(0.5, QColor(0xe9, 0x34, 0x43));
        self.redGradient.setColorAt(1.0, QColor(0xdc, 0x0c, 0x00));

    def setSize (self, size):
        self.badge_size = size

    def setCounter (self, counter):
        self.badge_counter = counter

    def getCounter (self):
        return self.badge_counter

    def paintEvent (self, event):
        QToolButton.paintEvent(self, event)
        p = QPainter(self)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setRenderHint(QPainter.Antialiasing)
        if self.badge_counter > 0:
            point = self.rect().topRight()
            self.drawBadge(p, point.x()-self.badge_size, point.y(), self.badge_size, str(self.badge_counter), QBrush(self.redGradient))

    def fillEllipse (self, painter, x, y, size, brush):
        path = QPainterPath()
        path.addEllipse(x, y, size, size);
        painter.fillPath(path, brush);

    def drawBadge(self, painter, x, y, size, text, brush):
        painter.setFont(QFont(painter.font().family(), 11, QFont.Bold))

        while ((size - painter.fontMetrics().width(text)) < 10):
            pointSize = painter.font().pointSize() - 1
            weight = QFont.Normal if (pointSize < 8) else QFont.Bold
            painter.setFont(QFont(painter.font().family(), painter.font().pointSize() - 1, weight))

        shadowColor = QColor(0, 0, 0, size)
        self.fillEllipse(painter, x + 1, y, size, shadowColor)
        self.fillEllipse(painter, x - 1, y, size, shadowColor)
        self.fillEllipse(painter, x, y + 1, size, shadowColor)
        self.fillEllipse(painter, x, y - 1, size, shadowColor)

        painter.setPen(QPen(Qt.white, 2));
        self.fillEllipse(painter, x, y, size - 3, brush)
        painter.drawEllipse(x, y, size - 2, size - 2)

        painter.setPen(QPen(Qt.white, 1));
        painter.drawText(x, y, size - 2, size - 2, Qt.AlignCenter, text);

if __name__ == '__main__':

    app = QApplication(sys.argv)
    win = QMainWindow()

    toolbar = QToolBar('Toolbar')
    win.addToolBar(Qt.BottomToolBarArea, toolbar)
    b = QToolBadgeButton(win)
    b.setText("test")
    b.setCounter(22)
    toolbar.addWidget(b)

    w = QBadgeButton(parent=win)
    w.setText("test")
    w.setCounter(22)
    win.setCentralWidget(w)
    win.show()

    sys.exit(app.exec_())

