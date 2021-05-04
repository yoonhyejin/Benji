#!/usr/bin/env python

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QLabel, QTextEdit, QRadioButton, QDateTimeEdit
from PyQt5.QtCore import QObject, pyqtSignal, QEvent, QDateTime, Qt
from PyQt5.QtGui import QPixmap, QCursor, QIcon
import webbrowser
import numpy as np
from datetime import datetime
import psycopg2

def clickable(widget):
    class Filter(QObject):
        clicked = pyqtSignal()

        def eventFilter(self, obj, event):

            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        return True
            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked

class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.datetime = QDateTime.currentDateTime()
        self.stats_url = "" #grafana web url

        #connect to sql
        self.conn = psycopg2.connect("host= dbname= user= password=") #postgresql connection information
        self.cur = self.conn.cursor()

        #get lateset status
        sql = "SELECT * from benji ORDER BY in_ts DESC LIMIT 1"
        self.cur.execute(sql)
        latest_row = self.cur.fetchone()
        if latest_row[3] == None:
            self.status = 'IN'
            self.confirm_msg = "Latest Status: {}, {}".format(self.status, datetime.strftime(latest_row[2], "%Y-%m-%d-%H:%M"))
        else:
            self.status = 'OUT'
            self.confirm_msg = "Latest Status: {}, {}".format(self.status, datetime.strftime(latest_row[3], "%Y-%m-%d-%H:%M"))

        #get images
        self.img_path = '/img/'
        self.sleep_img = QPixmap(self.img_path+'sleep.png')
        self.sleepy_img = QPixmap(self.img_path+'sleepy.png')
        self.awake_img = QPixmap(self.img_path+'awake.png')
        self.in_img =  QPixmap(self.img_path+'in.png')
        self.out_img =  QPixmap(self.img_path+'out.png')
        self.in_grey_img =  QPixmap(self.img_path+'in_grey.png')
        self.out_grey_img =  QPixmap(self.img_path+'out_grey.png')
        self.time_img = QPixmap(self.img_path+'time_img.png')
        self.msg_img = QPixmap(self.img_path+'msg_img.png')
        self.stats_img = QPixmap(self.img_path+'stats_img.png')

        self.initUI()

    def initUI(self):

        grid = QGridLayout()
        self.setLayout(grid)

        #title_img QLabel
        self.title_img = QLabel()
        self.title_img.setStyleSheet(self.hover_css())
        self.title_img.setAlignment(Qt.AlignCenter)
        grid.addWidget(self.title_img, 0,0,1,3)

        # ts QDateTimeEdit
        time_label = QLabel()
        time_label.setPixmap(self.time_img)
        grid.addWidget(time_label, 1,0)

        #now_btn QRadioButton
        self.now_btn = QRadioButton('Now')
        self.now_btn.setChecked(True)
        self.now_btn.setCursor(QCursor(Qt.PointingHandCursor))
        grid.addWidget(self.now_btn, 1,1,1,1)

        #manual_btn QRadioButton
        self.manual_btn = QRadioButton('Manually')
        self.manual_btn.setCursor(QCursor(Qt.PointingHandCursor))
        grid.addWidget(self.manual_btn, 1,2,1,1)

        #ts QDateTimeEdit
        self.ts = QDateTimeEdit(self)
        self.ts.setDateTime(self.datetime)
        self.ts.setDateTimeRange(QDateTime(1900, 1, 1, 00, 00, 00), QDateTime(2100, 1, 1, 00, 00, 00))
        self.ts.setDisplayFormat('yyyy.MM.dd hh:mm')
        grid.addWidget(self.ts, 2,2,1,1)

        # msg label
        msg_label = QLabel()
        msg_label.setPixmap(self.msg_img)
        grid.addWidget(msg_label, 3,0)

        #msg QTextEdit
        self.msg = QTextEdit()
        self.msg.setStyleSheet("background-color: white; border-radius: 10px; border: 3px solid white;")
        self.msg.installEventFilter(self)
        grid.addWidget(self.msg, 4,0,1,3)

        #in_btn, out_btn Qlabel
        self.in_btn = QLabel()
        self.in_btn.setAlignment(Qt.AlignCenter)
        self.in_btn.setCursor(QCursor(Qt.PointingHandCursor))

        self.out_btn = QLabel()
        self.out_btn.setAlignment(Qt.AlignCenter)
        self.out_btn.setCursor(QCursor(Qt.PointingHandCursor))


        grid.addWidget(self.in_btn, 5, 1)
        grid.addWidget(self.out_btn, 5, 2)

        #stats_btn QLabel
        stats_btn = QLabel()
        stats_btn.setPixmap(self.stats_img)
        stats_btn.setAlignment(Qt.AlignLeft)
        stats_btn.setCursor(QCursor(Qt.PointingHandCursor))
        grid.addWidget(stats_btn, 5, 0)

        # confirm text QLabel
        self.confirmlabel = QLabel(self.confirm_msg, self)
        grid.addWidget(self.confirmlabel, 6,0,1,3)


        #conditional images
        if self.status == 'IN':
            self.in_btn.setPixmap(self.in_grey_img)
            self.out_btn.setPixmap(self.out_img)
            self.title_img.setPixmap(self.awake_img)
        else:
            self.in_btn.setPixmap(self.in_img)
            self.out_btn.setPixmap(self.out_grey_img)
            self.title_img.setPixmap(self.sleep_img)

        ### EVENT ###
        clickable(self.in_btn).connect(self.inCheck)
        clickable(self.out_btn).connect(self.outCheck)
        clickable(stats_btn).connect(self.openWeb)

        self.setWindowTitle('BENJI')
        self.setStyleSheet("background-color: rgb(220,208,255);")
        self.setGeometry(300, 300, 300, 200)
        self.show()


    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Return:
                if self.status == 'OUT':
                    self.inCheck()
                else:
                    self.outCheck()
        return super().eventFilter(obj, event)

    def hover_css(self):
        hover_css_text = "".join(["QLabel{min-height:100px;}",
                                  "QLabel:hover{image:url(", self.img_path ,"sleepy.png);}"])
        return hover_css_text

    def inCheck(self):
        self.status = 'IN'
        self.datetime = QDateTime.currentDateTime()
        self.save()

        self.title_img.setPixmap(self.awake_img)
        self.in_btn.setPixmap(self.in_grey_img)
        self.out_btn.setPixmap(self.out_img)

    def outCheck(self):
        self.status = 'OUT'
        self.datetime = QDateTime.currentDateTime()
        self.save()

        self.title_img.setPixmap(self.sleep_img)
        self.out_btn.setPixmap(self.out_grey_img)
        self.in_btn.setPixmap(self.in_img)


    def openWeb(self):
        webbrowser.open(self.stats_url)

def save(self):

        if self.now_btn.isChecked():
            ts = datetime.now()
        else:
            ts = self.ts.dateTime().toPyDateTime()

        msg = self.msg.toPlainText()
        today = datetime.strftime(ts, '%Y%m%d')

        sql = "SELECT * from benji WHERE in_ts <= timestamp %s ORDER BY in_ts DESC LIMIT 1"
        self.cur.execute(sql, [ts])
        row = self.cur.fetchone()


        if self.status == 'IN' and (row == None or row[3] != None):
            #create new row
            sql = "INSERT INTO benji (dte, in_ts, out_ts, net_time, in_m, out_m) VALUES (%s,%s,%s,%s,%s,%s)"
            self.cur.execute(sql, [today, ts, None, 0, msg, ''])
            self.conn.commit()
            self.confirm_msg = "Status updated : {}, {}".format(datetime.strftime(ts, "%Y-%m-%d-%H:%M"), self.status)

        elif self.status == 'OUT' and row[3] == None:
            #update last row
            net_time = np.round(((ts - row[2]).seconds)/60,2)
            sql = "UPDATE benji SET out_ts = %s, net_time = %s, out_m = %s WHERE in_ts = %s"
            self.cur.execute(sql,[ts, net_time, msg ,row[2]])
            self.conn.commit()
            self.confirm_msg = "Status updated : {}, {}".format(datetime.strftime(ts, "%Y-%m-%d-%H:%M"), self.status)

        else:
            self.confirm_msg = "Your are trying to record {} twice in a row.".format(self.status)

        self.confirmlabel.setText(self.confirm_msg)
        self.datetime =  datetime.now()
        self.msg.setText(None)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    path = os.path.join('/img/awake.png')
    app.setWindowIcon(QIcon(path))
    ex = MyApp()
    sys.exit(app.exec_())
