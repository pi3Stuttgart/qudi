# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/Users/vladislavbushmakin/Desktop/qudi/gui/confocal/ui_change_to_LT.ui'
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
        self.Buttons = QtWidgets.QHBoxLayout()
        self.Buttons.setObjectName("Buttons")
        self.pushButton_confirm_LT = QtWidgets.QPushButton(Dialog_LT)
        self.pushButton_confirm_LT.setObjectName("pushButton_confirm_LT")
        self.Buttons.addWidget(self.pushButton_confirm_LT)
        self.pushButton_deny_LT = QtWidgets.QPushButton(Dialog_LT)
        self.pushButton_deny_LT.setObjectName("pushButton_deny_LT")
        self.Buttons.addWidget(self.pushButton_deny_LT)
        self.verticalLayout.addLayout(self.Buttons)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Dialog_LT)
        QtCore.QMetaObject.connectSlotsByName(Dialog_LT)

    def retranslateUi(self, Dialog_LT):
        _translate = QtCore.QCoreApplication.translate
        Dialog_LT.setWindowTitle(_translate("Dialog_LT", "LT limits"))
        self.label.setText(_translate("Dialog_LT", "<html><head/><body><p align=\"center\">Are you sure you are at low temperature?</p><p align=\"center\"><br/></p><p align=\"center\">Clicking yes will resunt in an increase of the piezo voltage range.</p><p align=\"center\"><span style=\" font-weight:600;\">This can break the piezos if you are not at LT!</span></p></body></html>"))
        self.pushButton_confirm_LT.setText(_translate("Dialog_LT", "Yes, I am at LT."))
        self.pushButton_deny_LT.setText(_translate("Dialog_LT", "No, take me back!"))

