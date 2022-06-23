# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Python\pi3diamond/qtgui/pi3d_main_window.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_window(object):
    def setupUi(self, window):
        window.setObjectName("window")
        window.resize(780, 569)
        window.setWindowOpacity(1.0)
        window.setAutoFillBackground(False)
        self.remove_next_script_button = QtWidgets.QPushButton(window)
        self.remove_next_script_button.setGeometry(QtCore.QRect(10, 480, 761, 31))
        self.remove_next_script_button.setObjectName("remove_next_script_button")
        self.add_to_queue_button = QtWidgets.QPushButton(window)
        self.add_to_queue_button.setGeometry(QtCore.QRect(10, 130, 531, 41))
        self.add_to_queue_button.setObjectName("add_to_queue_button")
        self.script_queue_table = QTableWidgetEnhancedDrop(window)
        self.script_queue_table.setEnabled(True)
        self.script_queue_table.setGeometry(QtCore.QRect(10, 180, 761, 291))
        self.script_queue_table.setAutoFillBackground(False)
        self.script_queue_table.setFrameShape(QtWidgets.QFrame.Panel)
        self.script_queue_table.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.script_queue_table.setObjectName("script_queue_table")
        self.script_queue_table.setColumnCount(0)
        self.script_queue_table.setRowCount(0)
        self.add_rco_button = QtWidgets.QPushButton(window)
        self.add_rco_button.setGeometry(QtCore.QRect(10, 90, 531, 31))
        self.add_rco_button.setObjectName("add_rco_button")
        self.evaluate_button = QtWidgets.QPushButton(window)
        self.evaluate_button.setGeometry(QtCore.QRect(550, 90, 221, 31))
        self.evaluate_button.setObjectName("evaluate_button")
        self.write_standard_awg_sequences_button = QtWidgets.QPushButton(window)
        self.write_standard_awg_sequences_button.setGeometry(QtCore.QRect(550, 130, 221, 41))
        self.write_standard_awg_sequences_button.setObjectName("write_standard_awg_sequences_button")
        self.set_stop_request_button = QtWidgets.QPushButton(window)
        self.set_stop_request_button.setGeometry(QtCore.QRect(10, 520, 761, 41))
        self.set_stop_request_button.setObjectName("set_stop_request_button")
        self.selected_user_script_combo_box = QtWidgets.QComboBox(window)
        self.selected_user_script_combo_box.setGeometry(QtCore.QRect(10, 50, 531, 31))
        self.selected_user_script_combo_box.setMaxVisibleItems(40)
        self.selected_user_script_combo_box.setObjectName("selected_user_script_combo_box")
        self.user_script_folder_text_field = QtWidgets.QTextBrowser(window)
        self.user_script_folder_text_field.setEnabled(True)
        self.user_script_folder_text_field.setGeometry(QtCore.QRect(10, 10, 491, 31))
        self.user_script_folder_text_field.setReadOnly(False)
        self.user_script_folder_text_field.setObjectName("user_script_folder_text_field")
        self.user_script_params_text_field = QtWidgets.QTextEdit(window)
        self.user_script_params_text_field.setEnabled(False)
        self.user_script_params_text_field.setGeometry(QtCore.QRect(550, 10, 221, 71))
        self.user_script_params_text_field.setObjectName("user_script_params_text_field")
        self.user_script_folder_pushButton = QtWidgets.QPushButton(window)
        self.user_script_folder_pushButton.setGeometry(QtCore.QRect(510, 10, 31, 31))
        self.user_script_folder_pushButton.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("folder_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.On)
        self.user_script_folder_pushButton.setIcon(icon)
        self.user_script_folder_pushButton.setIconSize(QtCore.QSize(16, 16))
        self.user_script_folder_pushButton.setObjectName("user_script_folder_pushButton")

        self.retranslateUi(window)
        QtCore.QMetaObject.connectSlotsByName(window)

    def retranslateUi(self, window):
        _translate = QtCore.QCoreApplication.translate
        window.setWindowTitle(_translate("window", "Form"))
        self.remove_next_script_button.setText(_translate("window", "Remove next script"))
        self.add_to_queue_button.setText(_translate("window", "Add Script"))
        self.add_rco_button.setText(_translate("window", "Add refocus_confocal_odmr"))
        self.evaluate_button.setText(_translate("window", "run script evaluate"))
        self.write_standard_awg_sequences_button.setText(_translate("window", "Write sequences"))
        self.set_stop_request_button.setText(_translate("window", "Set stop_request"))

from qutip_enhanced.qtgui.custom_widgets import QTableWidgetEnhancedDrop
