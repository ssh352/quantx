
# -*- coding: utf-8 -*-

# Copyright (c) 2018-2018 the QuantX authors
# All rights reserved.
#
# The project sponsor and lead author is Xu Rendong.
# E-mail: xrd@ustc.edu, QQ: 277195007, WeChat: ustc_xrd
# See the contributors file for names of other contributors.
#
# Commercial use of this code in source and binary forms is
# governed by a LGPL v3 license. You may get a copy from the
# root directory. Or else you should get a specific written 
# permission from the project author.
#
# Individual and educational use of this code in source and
# binary forms is governed by a 3-clause BSD license. You may
# get a copy from the root directory. Certainly welcome you
# to contribute code of all sorts.
#
# Be sure to retain the above copyright notice and conditions.

from PyQt5.QtGui import QColor, QFont, QPalette, QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QHBoxLayout, QVBoxLayout

import define

class AboutDialog(QDialog):
    def __init__(self, parent):
        super(AboutDialog, self).__init__(parent)
        self.parent = parent
        self.InitUserInterface()

    def __del__(self):
        pass

    def InitUserInterface(self):
        win_size_x = 390
        win_size_y = 230
        
        self.setWindowTitle("关于")
        self.resize(win_size_x, win_size_y)
        self.setWindowOpacity(0.85)
        
        self.label_title = QLabel()
        self.label_title.setText(define.APP_TITLE_EN)
        self.label_title.setAlignment(Qt.AlignCenter)
        self.label_title.setFont(QFont("YaHei", 20))
        palette_title = QPalette()
        palette_title.setColor(QPalette.WindowText, QColor(128, 0, 0))
        self.label_title.setPalette(palette_title)
        
        self.label_version = QLabel()
        self.label_version.setText(define.APP_VERSION)
        self.label_version.setAlignment(Qt.AlignCenter)
        self.label_version.setFont(QFont("YaHei", 9))
        
        self.label_icon = QLabel()
        self.label_icon.setAlignment(Qt.AlignCenter)
        self.label_icon.setPixmap(QPixmap(define.DEF_ICON_ABOUT_DIALOG))
        
        self.label_developer = QLabel()
        self.label_developer.setText(define.APP_DEVELOPER)
        self.label_developer.setAlignment(Qt.AlignCenter)
        self.label_developer.setFont(QFont("YaHei", 9))
        
        self.label_company = QLabel()
        self.label_company.setText(define.APP_COMPANY)
        self.label_company.setAlignment(Qt.AlignCenter)
        self.label_company.setFont(QFont("YaHei", 9))
        
        self.label_copyright = QLabel()
        self.label_copyright.setText(define.APP_COPYRIGHT)
        self.label_copyright.setAlignment(Qt.AlignCenter)
        self.label_copyright.setFont(QFont("YaHei", 9))
        
        self.button_ok = QPushButton("确  定")
        self.button_ok.setFont(QFont("YaHei", 9))
        self.button_ok.clicked.connect(self.OnButtonClicked)
        
        self.h_box = QHBoxLayout()
        self.h_box.addStretch(1)
        self.h_box.addWidget(self.button_ok)
        self.h_box.addStretch(1)
        
        self.v_box = QVBoxLayout()
        self.v_box.addWidget(self.label_title)
        self.v_box.addWidget(self.label_version)
        self.v_box.addWidget(self.label_icon)
        self.v_box.addStretch(1)
        self.v_box.addWidget(self.label_developer)
        self.v_box.addWidget(self.label_company)
        self.v_box.addWidget(self.label_copyright)
        self.v_box.addLayout(self.h_box)
        
        self.setLayout(self.v_box)

    def OnButtonClicked(self):
        self.close()
