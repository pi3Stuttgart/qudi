# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/vladislavbushmakin/Desktop/qudi/gui/confocal/ui_confirm_change.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog_LT(object):
    def setupUi(self, Dialog_LT):
        Dialog_LT.setObjectName("Dialog_LT")
        Dialog_LT.resize(400, 257)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog_LT)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(Dialog_LT)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.pushButton_okay = QtWidgets.QPushButton(Dialog_LT)
        self.pushButton_okay.setObjectName("pushButton_okay")
        self.verticalLayout.addWidget(self.pushButton_okay)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Dialog_LT)
        QtCore.QMetaObject.connectSlotsByName(Dialog_LT)

    def retranslateUi(self, Dialog_LT):
        _translate = QtCore.QCoreApplication.translate
        Dialog_LT.setWindowTitle(_translate("Dialog_LT", "LT limits changed"))
        self.label.setText(_translate("Dialog_LT", "<html><head/><body><p align=\"center\">LT limits have been set</p></body></html>"))
        self.pushButton_okay.setText(_translate("Dialog_LT", "okay"))

