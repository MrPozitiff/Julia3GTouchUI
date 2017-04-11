#!/usr/bin/python
from PyQt4 import QtCore, QtGui
import mainGUI
import keyBoard
import time
import sys
import subprocess
from octoprintAPI import octoprintAPI
from hurry.filesize import size
from datetime import datetime
from functools import partial
import qrcode
# pip install websocket-client
import websocket
import json
import random
import uuid
import os
import serial
import io
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)  # Use the board numbering scheme
GPIO.setwarnings(False)  # Disable GPIO warnings

# TODO:
'''

# Remove SD card capability from octoprint settings
# Should add error/status checking in the response in some functions in the octoprintAPI
# session keys??
# printer status should show errors from printer.
# async requests
# http://eli.thegreenplace.net/2011/04/25/passing-extra-arguments-to-pyqt-slot
# fix wifi
# status bar netweorking and wifi stuff
# reconnect to printer using GUI
# check if disk is getting full
# recheck for internet being conneted, refresh button
# load filaments from a file
# store settings to a file




#settings should show the current wifi
#clean up keyboard nameing
#add asertions and exeptions
#disaable done button if empty
#oncancel change filament cooldown
#toggle temperature indipendant of motion
#get active extruder from motion controller. when pausing, note down and resume with active extruder
#QR code has dictionary with IP address also

Testing:
# handle nothing selected in file select menus when deleting and printing etc.
# Delete items from local and USB
# different file list pages for local and USB
# test USB/Local properly
# check for uploading error when uploading from USB
# Test if active extruder goes back after pausing
# TRy to fuck with printing process from GUI
# PNG Handaling
# dissable buttons while printing
'''

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++Global variables++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


# ip = '192.168.0.118:5000'
ip = '0.0.0.0:5000'
# ip = 'localhost:5000'
# open octoprint config.yaman and get the apiKey
# apiKey = 'E85D3D2FFAF446BC8B763F2D3DB46D01'
apiKey = 'B508534ED20348F090B4D0AD637D3660'
file_name = ''
Development = True
filaments = {"ABS": 220,
             "PLA": 200,
             "NinjaFlex": 220,
             "PolyCarbonate": 280,
             "XT-Copolymer": 240,
             "FilaFlex": 210,
             "Nylon": 250,
             "Scaffold": 210,
             "WoodFill": 200,
             "CopperFill": 180
             }

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


def run_async(func):
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


class buzzerFeedback(object):
    def __init__(self, buzzerPin):
        GPIO.cleanup()
        self.buzzerPin = buzzerPin
        GPIO.setup(self.buzzerPin, GPIO.OUT)
        GPIO.output(self.buzzerPin, GPIO.LOW)

    @run_async
    def buzz(self):
        GPIO.output(self.buzzerPin, (GPIO.HIGH))
        time.sleep(0.005)
        GPIO.output(self.buzzerPin, GPIO.LOW)


buzzer = buzzerFeedback(12)

'''
To get the buzzer to beep on button press
'''

OriginalPushButton = QtGui.QPushButton
OriginalToolButton = QtGui.QToolButton


class QPushButtonFeedback(QtGui.QPushButton):
    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        OriginalPushButton.mousePressEvent(self, QMouseEvent)


class QToolButtonFeedback(QtGui.QToolButton):
    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        OriginalToolButton.mousePressEvent(self, QMouseEvent)


QtGui.QToolButton = QToolButtonFeedback
QtGui.QPushButton = QPushButtonFeedback


class Image(qrcode.image.base.BaseImage):
    def __init__(self, border, width, box_size):
        self.border = border
        self.width = width
        self.box_size = box_size
        size = (width + border * 2) * box_size
        self._image = QtGui.QImage(
            size, size, QtGui.QImage.Format_RGB16)
        self._image.fill(QtCore.Qt.white)

    def pixmap(self):
        return QtGui.QPixmap.fromImage(self._image)

    def drawrect(self, row, col):
        painter = QtGui.QPainter(self._image)
        painter.fillRect(
            (col + self.border) * self.box_size,
            (row + self.border) * self.box_size,
            self.box_size, self.box_size,
            QtCore.Qt.black)

    def save(self, stream, kind=None):
        pass


class clickableLineEdit(QtGui.QLineEdit):
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)

    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        self.emit(QtCore.SIGNAL("clicked()"))


class Keyboard(QtGui.QDialog, keyBoard.Ui_Form):
    '''
    Class that sets up the Keyboard UI and functionality
    '''

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.setupUi(self)
        self.setActions()
        self.textEdit.setText("")

    def setActions(self):
        # self.pushButton.clicked.connect(partial(self.add, self.pushButton.text()))
        # self.pushButton_2.clicked.connect(partial(self.window1.stopAction(), self.lineEdit.text()))
        self.ButtonEnter.clicked.connect(self.enterKeyBoardValue)
        self.ButtonEnter2.clicked.connect(self.enterKeyBoardValue)
        self.ButtonEnter3.clicked.connect(self.KeyBoardHome)
        self.ButtonNumeric.clicked.connect(self.Numeric)
        self.ButtonNumeric2.clicked.connect(self.Numeric)
        self.ButtonLowerCase.clicked.connect(self.LowerCase)
        self.ButtonUpperCase.clicked.connect(self.UpperCase)
        self.ButtonSpace.clicked.connect(self.enterSpace)
        self.ButtonSpace2.clicked.connect(self.enterSpace)
        self.ButtonBackSpace.clicked.connect(self.backSpace)
        self.ButtonBackSpace2.clicked.connect(self.backSpace)
        # for i in range(5):
        # list = [self.pushButton, self.pushButton_1, self.pushButton_4]
        for i in range(1, 95):
            temp = "Button" + str(i)
            button = getattr(self, temp)
            button.clicked.connect(partial(self.add, button.text()))
            # button.clicked.connect(lambda: self.add(text))

    def LowerCase(self):
        self.stackedWidget.setCurrentWidget(self.page_2)

    def UpperCase(self):
        self.stackedWidget.setCurrentWidget(self.page)

    def KeyBoardHome(self):
        self.stackedWidget.setCurrentWidget(self.page)

    def Numeric(self):
        self.stackedWidget.setCurrentWidget(self.page_11)

    def enterKeyBoardValue(self):
        self.close()
        MainWindow.getKeyboadText(self.textEdit.toPlainText())
        self.textEdit.setText("")

    def enterSpace(self):
        self.textEdit.setText(self.textEdit.toPlainText() + " ")

    def backSpace(self):
        st = self.textEdit.toPlainText()
        self.textEdit.setText(st[:-1])

    def add(self, arg):
        self.textEdit.setText(self.textEdit.toPlainText() + arg)


class MainUiClass(QtGui.QMainWindow, mainGUI.Ui_MainWindow):
    '''
    Main GUI Workhorse, all slots and events defined within
    The main implementation class that inherits methods, variables etc from mainGUI.py and QMainWindow
    '''

    def setupUi(self, MainWindow):
        super(MainUiClass, self).setupUi(MainWindow)
        self.wifiPasswordLineEdit = clickableLineEdit(self.wifiSettingsPage)
        self.wifiPasswordLineEdit.setGeometry(QtCore.QRect(0, 170, 480, 60))
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Gotham"))
        font.setPointSize(15)
        self.wifiPasswordLineEdit.setFont(font)
        self.wifiPasswordLineEdit.setStyleSheet(_fromUtf8("background-color: rgb(255, 255, 255);\n"
                                                          ""))
        self.wifiPasswordLineEdit.setObjectName(_fromUtf8("wifiPasswordLineEdit"))

        self.movie = QtGui.QMovie("png/loading.gif")
        self.loadingGif.setMovie(self.movie)
        self.movie.start()

        self.movie1 = QtGui.QMovie("png/unlockAll.gif")
        self.releaseAllLevelingScrewsLabel.setMovie(self.movie1)

        self.movie2 = QtGui.QMovie("png/lockRight.gif")
        self.turnRightLevelingScrewLabel.setMovie(self.movie2)

        self.movie3 = QtGui.QMovie("png/lockLeft.gif")
        self.turnLeftLevelingScrewLabel.setMovie(self.movie3)

        self.movie4 = QtGui.QMovie("png/lockCenter.gif")
        self.turnCenterLevelingScrewLabel.setMovie(self.movie4)

        self.movie5 = QtGui.QMovie("png/cat.gif")
        self.caliberationHeightLabel.setMovie(self.movie5)

    def __init__(self):
        '''
        This method gets called when an object of type MainUIClass is defined
        '''
        super(MainUiClass, self).__init__()
        # Calls setupUi that sets up layout and geometry of all UI elements
        self.setupUi(self)
        self.stackedWidget.setCurrentWidget(self.loadingPage)
        self.setStep(10)
        self.keyboardWindow = None
        self.changeFilamentHeatingFlag = False
        self.setHomeOffsetBool = False
        self.currentImage = None
        self.currentFile = None
        '''
        The setLEDFromStatus flag is used to change the status of the lightbar from the updateStatus/updatePrintStatus
        methods that get called from octoptint, or should the LED's be get because of some external event, like caliberation,
        filament getting over etc.'''
        self.setLEDFromStatus = True
        self.setActiveExtruder(0)
        # flags for keyboard input. Depending on these flags, keyboard will enter into appropriate line edit
        self.enterIntoSSID = False
        self.enterIntoPassword = False
        self.sanityCheck = sanityCheckThread()
        self.sanityCheck.start()
        self.connect(self.sanityCheck, QtCore.SIGNAL('LOADED'), self.proceed)

        # Thread to get the get the state of the Printer as well as the temperature

    def proceed(self):
        '''
        Startes websocket, as well as initialises button actions and callbacks. THis is done in such a manner so that the callbacks that dnepend on websockets
        load only after the socket is available which in turn is dependent on the server being available which is checked in the sanity check thread
        '''
        self.QtSocket = QtWebsocket()
        self.QtSocket.start()
        self.setActions()
        self.movie.stop()
        self.stackedWidget.setCurrentWidget(MainWindow.homePage)

    def setActions(self):

        '''
        defines all the Slots and Button events.
        '''
        self.connect(self.QtSocket, QtCore.SIGNAL('SET_Z_HOME_OFFSET'), self.setZHomeOffset)
        self.connect(self.QtSocket, QtCore.SIGNAL('Z_HOME_OFFSET'), self.setZHomeOffsestUI)
        self.connect(self.QtSocket, QtCore.SIGNAL('ACTIVE_EXTRUDER'), self.setActiveExtruder)
        self.connect(self.QtSocket, QtCore.SIGNAL('TEMPERATURES'), self.updateTemperature)
        self.connect(self.QtSocket, QtCore.SIGNAL('STATUS'), self.updateStatus)
        self.connect(self.QtSocket, QtCore.SIGNAL('PRINT_STATUS'), self.updatePrintStatus)
        self.connect(self.QtSocket, QtCore.SIGNAL('FILAMENT_SENSOR_TRIGGERED'), self.filamentSensorTriggeredMessageBox)
        self.connect(self.wifiPasswordLineEdit, QtCore.SIGNAL("clicked()"), self.startKeyboardPassword)


        # Button Events:

        # Home Screen:
        self.stopButton.pressed.connect(self.stopAction)
        # self.menuButton.pressed.connect(self.keyboardButton)
        self.menuButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.controlButton.pressed.connect(self.control)
        self.playPauseButton.clicked.connect(self.playPauseAction)

        # MenuScreen
        self.menuBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
        self.menuControlButton.pressed.connect(self.control)
        self.menuPrintButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.menuCaliberateButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.caliberatePage))
        self.menuSettingsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # Caliberate Page
        self.caliberateBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.nozzleOffsetButton.pressed.connect(self.nozzleOffset)
        # the -ve sign is such that its converted to home offset and not just distance between nozzle and bed
        self.nozzleOffsetSetButton.pressed.connect(
            lambda: self.setZHomeOffset(self.nozzleOffsetDoubleSpinBox.value(), True))
        self.nozzleOffsetBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.caliberatePage))

        self.caliberationWizardButton.clicked.connect(self.step1)
        self.step1NextButton.clicked.connect(self.step2)
        self.step2NextButton.clicked.connect(self.step3)
        self.step3NextButton.clicked.connect(self.step4)
        self.step4NextButton.clicked.connect(self.step5)
        self.step5NextButton.clicked.connect(self.step6)
        self.step6NextButton.clicked.connect(self.step7)
        self.step7NextButton.clicked.connect(self.step8)
        self.step8DoneButton.clicked.connect(self.doneStep)
        self.moveZMCaliberateButton.pressed.connect(lambda: octopiclient.jog(z=-0.05))
        self.moveZPCaliberateButton.pressed.connect(lambda: octopiclient.jog(z=0.05))
        self.step1CancelButton.pressed.connect(self.cancelStep)
        self.step2CancelButton.pressed.connect(self.cancelStep)
        self.step3CancelButton.pressed.connect(self.cancelStep)
        self.step4CancelButton.pressed.connect(self.cancelStep)
        self.step5CancelButton.pressed.connect(self.cancelStep)
        self.step6CancelButton.pressed.connect(self.cancelStep)
        self.step7CancelButton.pressed.connect(self.cancelStep)
        self.step8CancelButton.pressed.connect(self.cancelStep)

        # PrintLocationScreen
        self.printLocationScreenBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.fromLocalButton.pressed.connect(self.fileListLocal)
        self.fromUsbButton.pressed.connect(self.fileListUSB)

        # fileListLocalScreen
        self.localStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.localStorageScrollUp.pressed.connect(
            lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() - 1))
        self.localStorageScrollDown.pressed.connect(
            lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() + 1))
        self.localStorageSelectButton.pressed.connect(self.printSelectedLocal)
        self.localStorageDeleteButton.pressed.connect(self.deleteItem)

        # selectedFile Local Screen
        self.fileSelectedBackButton.pressed.connect(self.fileListLocal)
        self.fileSelectedPrintButton.pressed.connect(self.printFile)

        # filelistUSBPage
        self.USBStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.USBStorageScrollUp.pressed.connect(
            lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() - 1))
        self.USBStorageScrollDown.pressed.connect(
            lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() + 1))
        self.USBStorageSelectButton.pressed.connect(self.printSelectedUSB)
        self.USBStorageSaveButton.pressed.connect(lambda: self.transferToLocal(prnt=False))

        # selectedFile USB Screen
        self.fileSelectedUSBBackButton.pressed.connect(self.fileListUSB)
        self.fileSelectedUSBTransferButton.pressed.connect(lambda: self.transferToLocal(prnt=False))
        self.fileSelectedUSBPrintButton.pressed.connect(lambda: self.transferToLocal(prnt=True))

        # ControlScreen
        self.moveYPButton.pressed.connect(lambda: octopiclient.jog(y=self.step))
        self.moveYMButton.pressed.connect(lambda: octopiclient.jog(y=-self.step))
        self.moveXMButton.pressed.connect(lambda: octopiclient.jog(x=-self.step))
        self.moveXPButton.pressed.connect(lambda: octopiclient.jog(x=self.step))
        self.moveZPButton.pressed.connect(lambda: octopiclient.jog(z=self.step))
        self.moveZMButton.pressed.connect(lambda: octopiclient.jog(z=-self.step))
        self.extruderButton.pressed.connect(lambda: octopiclient.extrude(self.step))
        self.retractButton.pressed.connect(lambda: octopiclient.extrude(-self.step))
        self.motorOffButton.pressed.connect(lambda: octopiclient.gcode(command='M18'))
        self.fanOnButton.pressed.connect(lambda: octopiclient.gcode(command='M106'))
        self.fanOffButton.pressed.connect(lambda: octopiclient.gcode(command='M107'))
        self.cooldownButton.pressed.connect(self.coolDownAction)
        self.step0_1Button.pressed.connect(lambda: self.setStep(0.1))
        self.step1Button.pressed.connect(lambda: self.setStep(1))
        self.step10Button.pressed.connect(lambda: self.setStep(10))
        self.homeXYButton.pressed.connect(lambda: octopiclient.home(['x', 'y']))
        self.homeZButton.pressed.connect(lambda: octopiclient.home(['z']))
        self.toolToggleTemperatureButton.clicked.connect(self.selectToolTemperature)
        self.toolToggleMotionButton.clicked.connect(self.selectToolMotion)
        self.controlBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
        self.setToolTempButton.pressed.connect(lambda: octopiclient.setToolTemperature({
            "tool1": self.toolTempSpinBox.value()}) if self.toolToggleTemperatureButton.isChecked() else octopiclient.setToolTemperature(
            self.toolTempSpinBox.value()))
        self.setBedTempButton.pressed.connect(lambda: octopiclient.setBedTemperature(self.bedTempSpinBox.value()))
        self.setFlowRateButton.pressed.connect(lambda: octopiclient.flowrate(self.flowRateSpinBox.value()))
        self.setFeedRateButton.pressed.connect(lambda: octopiclient.feedrate(self.feedRateSpinBox.value()))
        self.filamentSensorToggleButton.clicked.connect(self.toggleFilamentSensor)

        # ChangeFilament rutien
        self.changeFilamentButton.pressed.connect(self.changeFilament)
        self.toolToggleChangeFilamentButton.clicked.connect(self.selectToolChangeFilament)
        self.changeFilamentBackButton.pressed.connect(self.control)
        self.changeFilamentBackButton2.pressed.connect(self.control)
        self.changeFilamentUnloadButton.pressed.connect(lambda: self.unloadFilament())
        self.changeFilamentLoadButton.pressed.connect(lambda: self.loadFilament())
        self.loadDoneButton.pressed.connect(self.control)
        self.unloadDoneButton.pressed.connect(self.changeFilament)
        self.retractFilamentButton.pressed.connect(lambda: octopiclient.extrude(-10))
        self.ExtrudeButton.pressed.connect(lambda: octopiclient.extrude(10))

        #Settings Page
        self.settingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.pairPhoneButton.pressed.connect(self.pairPhoneApp)
        self.configureWifiButton.pressed.connect(self.wifiSettings)
        self.networkInfoButton.pressed.connect(self.networkInfo)

        #Network Info Page
        self.networkInfoBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # WifiSetings page
        self.wifiSettingsSSIDKeyboardButton.pressed.connect(self.startKeyboardSSID)
        self.wifiSettingsCancelButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
        self.wifiSettingsDoneButton.pressed.connect(self.acceptWifiSettings)

        # QR Code
        self.QRCodeBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # ++++++++++++++++++Function Definitions++++++++++++++++++++++++++++++++++++++++
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def filamentSensorTriggeredMessageBox(self):
        '''
        Displays a message box alerting the user of a filament error
        '''
        self.activeExtruderPrint = self.activeExtruder
        choice = QtGui.QMessageBox()
        choice.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        font = QtGui.QFont()
        QtGui.QInputMethodEvent
        font.setFamily(_fromUtf8("Gotham"))
        font.setPointSize(14)
        font.setBold(False)
        font.setUnderline(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        choice.setFont(font)
        choice.setText("Filament Error detected on tool " + str(self.activeExtruder))
        choice.setIconPixmap(QtGui.QPixmap(_fromUtf8("png/exclamation-mark.png")))
        # choice.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        choice.setGeometry(QtCore.QRect(110, 50, 200, 300))
        choice.setStandardButtons(QtGui.QMessageBox.Ok)
        choice.setStyleSheet(_fromUtf8("\n"
                                       "QMessageBox{\n"
                                       "height:300px;\n"
                                       "width: 400px;\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton{\n"
                                       "     border: 1px solid rgb(87, 87, 87);\n"
                                       "    background-color: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0.188, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(255, 255, 255, 255));\n"
                                       "height:70px;\n"
                                       "width: 150px;\n"
                                       "border-radius:5px;\n"
                                       "    font: 14pt \"Gotham\";\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton:pressed {\n"
                                       "    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,\n"
                                       "                                      stop: 0 #dadbde, stop: 1 #f6f7fa);\n"
                                       "}\n"
                                       "QPushButton:focus {\n"
                                       "outline: none;\n"
                                       "}\n"

                                       "\n"
                                       ""))
        retval = choice.exec_()
        if retval == QtGui.QMessageBox.Ok:
            pass

    def toggleFilamentSensor(self):
        self.filamentSensorToggleButton.setText(
            "FilaSensor ON") if self.filamentSensorToggleButton.isChecked() else self.filamentSensorToggleButton.setText(
            "FilaSensor OFF")
        if self.filamentSensorToggleButton.isChecked():
            print "FilaSensor ON"
            octopiclient.toggleFiamentSensor(2)
        else:
            print "FilaSensor OFF"
            octopiclient.toggleFiamentSensor(-1)

    def acceptWifiSettings(self):
        wlan0_config_file = io.open("/etc/wpa_supplicant/wpa_supplicant.conf", "r+", encoding='utf8')
        wlan0_config_file.truncate()
        ascii_ssid = self.wifiSettingsComboBox.currentText()
        # unicode_ssid = ascii_ssid.decode('string_escape').decode('utf-8')
        wlan0_config_file.write(u"network={\n")
        wlan0_config_file.write(u'ssid="' + str(ascii_ssid) + '"\n')
        if self.hiddenCheckBox.isChecked():
            wlan0_config_file.write(u'scan_ssid=1\n')
        if str(self.wifiPasswordLineEdit.text()) != "":
            wlan0_config_file.write(u'psk="' + str(self.wifiPasswordLineEdit.text()) + '"\n')
        wlan0_config_file.write(u'}')
        wlan0_config_file.close()
        self.restartNetworkingThreadObject = restartNetworkingThread()
        self.restartNetworkingThreadObject.start()
        self.connect(self.restartNetworkingThreadObject, QtCore.SIGNAL('IP_ADDRESS'), self.wifiReturnFunction)
        self.restartNetworkingMessageBox()

    def wifiReturnFunction(self, x):
        if x != None:
            self.wifiMessageBox.setText('Connected, IP: ' + x)
            self.wifiMessageBox.setStandardButtons(QtGui.QMessageBox.Ok)
        else:
            self.wifiMessageBox.setText("Not able to connect to WiFi")

    def startKeyboardPassword(self):
        '''
        starts the keyboard screen for entering Password
        '''
        if self.keyboardWindow is None:
            self.keyboardWindow = Keyboard(self)
        self.keyboardWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.keyboardWindow.show()
        # flag that will be used to know where to enter text
        self.enterIntoPassword = True

    def startKeyboardSSID(self):
        '''
        starts the keyboard screen for entering SSID
        '''
        if self.keyboardWindow is None:
            self.keyboardWindow = Keyboard(self)
        self.keyboardWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.keyboardWindow.show()
        # flag that will be used to know where to enter text
        self.enterIntoSSID = True

    def getKeyboadText(self, text):

        '''
        Enters value reieved from the keyboard into appropriate fields
        :param text: text to enter into appropriate field
        :return: None
        '''
        if self.enterIntoPassword:
            self.enterIntoPassword = False
            self.wifiPasswordLineEdit.setText(text)
        elif self.enterIntoSSID:
            self.wifiSettingsComboBox.addItem(text)
            self.wifiSettingsComboBox.setCurrentIndex(self.wifiSettingsComboBox.findText(text))
            self.enterIntoSSID = False
        self.keyboardWindow = None

    def scan_wifi(self):
        '''
        uses linux shell and WIFI interface to scan available networks
        :return: dictionary of the SSID and the signal strength
        '''
        # scanData = {}
        # print "Scanning available wireless signals available to wlan0"
        scan_result = \
        subprocess.Popen("iwlist wlan0 scan | grep 'ESSID'", stdout=subprocess.PIPE, shell=True).communicate()[0]
        # Processing STDOUT into a dictionary that later will be converted to a json file later
        scan_result = scan_result.split('ESSID:')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
        scan_result = [s.strip() for s in scan_result]
        scan_result = [s.strip('"') for s in scan_result]
        scan_result = filter(None, scan_result)
        return scan_result

    def updateTemperature(self, temperature):
        '''
        Slot that gets a signal originating from the thread that keeps polling for printer status
        runs at 1HZ, so do things that need to be constantly updated only
        :param temperature: dict containing key:value pairs with keys being the tools, bed and their values being their corresponding temperratures
        '''

        if temperature['tool0Target'] == 0:
            self.tool0TempBar.setMaximum(300)
            self.tool0TempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                      "    border-radius: 5px;\n"
                                                      "    background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.522, y2:0, stop:0.0336134 rgba(74, 183, 255, 255), stop:1 rgba(53, 173, 242, 255));\n"
                                                      "}\n"
                                                      "\n"
                                                      "QProgressBar {\n"
                                                      "    border: 1px solid white;\n"
                                                      "    border-radius: 5px;\n"
                                                      "}\n"
                                                      ""))
        elif temperature['tool0Actual'] <= temperature['tool0Target']:
            self.tool0TempBar.setMaximum(temperature['tool0Target'])
            self.tool0TempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                      "\n"
                                                      "    background-color: qlineargradient(spread:pad, x1:0.492, y1:0, x2:0.487, y2:0, stop:0 rgba(255, 28, 35, 255), stop:1 rgba(255, 68, 74, 255));\n"
                                                      "    border-radius: 5px;\n"
                                                      "\n"
                                                      "}\n"
                                                      "\n"
                                                      "QProgressBar {\n"
                                                      "    border: 1px solid white;\n"
                                                      "    border-radius: 5px;\n"
                                                      "}\n"
                                                      ""))
        else:
            self.tool0TempBar.setMaximum(temperature['tool0Actual'])
        self.tool0TempBar.setValue(temperature['tool0Actual'])
        self.tool0ActualTemperature.setText(str(temperature['tool0Actual']))  # + unichr(176)
        self.tool0TargetTemperature.setText(str(temperature['tool0Target']))

        if temperature['tool1Target'] == 0:
            self.tool1TempBar.setMaximum(300)
            self.tool1TempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                      "    border-radius: 5px;\n"
                                                      "    background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.522, y2:0, stop:0.0336134 rgba(74, 183, 255, 255), stop:1 rgba(53, 173, 242, 255));\n"
                                                      "}\n"
                                                      "\n"
                                                      "QProgressBar {\n"
                                                      "    border: 1px solid white;\n"
                                                      "    border-radius: 5px;\n"
                                                      "}\n"
                                                      ""))
        elif temperature['tool1Actual'] <= temperature['tool0Target']:
            self.tool1TempBar.setMaximum(temperature['tool0Target'])
            self.tool1TempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                      "\n"
                                                      "    background-color: qlineargradient(spread:pad, x1:0.492, y1:0, x2:0.487, y2:0, stop:0 rgba(255, 28, 35, 255), stop:1 rgba(255, 68, 74, 255));\n"
                                                      "    border-radius: 5px;\n"
                                                      "\n"
                                                      "}\n"
                                                      "\n"
                                                      "QProgressBar {\n"
                                                      "    border: 1px solid white;\n"
                                                      "    border-radius: 5px;\n"
                                                      "}\n"
                                                      ""))
        else:
            self.tool1TempBar.setMaximum(temperature['tool1Actual'])
        self.tool1TempBar.setValue(temperature['tool1Actual'])
        self.tool1ActualTemperature.setText(str(temperature['tool1Actual']))  # + unichr(176)
        self.tool1TargetTemperature.setText(str(temperature['tool1Target']))

        if temperature['bedTarget'] == 0:
            self.bedTempBar.setMaximum(150)
            self.bedTempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                    "    border-radius: 5px;\n"
                                                    "    background-color: qlineargradient(spread:pad, x1:0.517, y1:0, x2:0.522, y2:0, stop:0.0336134 rgba(74, 183, 255, 255), stop:1 rgba(53, 173, 242, 255));\n"
                                                    "}\n"
                                                    "\n"
                                                    "QProgressBar {\n"
                                                    "    border: 1px solid white;\n"
                                                    "    border-radius: 5px;\n"
                                                    "}\n"
                                                    ""))
        elif temperature['bedActual'] <= temperature['bedTarget']:
            self.bedTempBar.setMaximum(temperature['bedTarget'])
            self.bedTempBar.setStyleSheet(_fromUtf8("QProgressBar::chunk {\n"
                                                    "\n"
                                                    "    background-color: qlineargradient(spread:pad, x1:0.492, y1:0, x2:0.487, y2:0, stop:0 rgba(255, 28, 35, 255), stop:1 rgba(255, 68, 74, 255));\n"
                                                    "    border-radius: 5px;\n"
                                                    "\n"
                                                    "}\n"
                                                    "\n"
                                                    "QProgressBar {\n"
                                                    "    border: 1px solid white;\n"
                                                    "    border-radius: 5px;\n"
                                                    "}\n"
                                                    ""))
        else:
            self.bedTempBar.setMaximum(temperature['bedActual'])
        self.bedTempBar.setValue(temperature['bedActual'])
        self.bedActualTemperatute.setText(str(temperature['bedActual']))  # + unichr(176))
        self.bedTargetTemperature.setText(str(temperature['bedTarget']))  # + unichr(176))

        # updates the progress bar on the change filament screen
        if self.changeFilamentHeatingFlag:
            if self.activeExtruder == 0:
                if temperature['tool0Target'] == 0:
                    self.changeFilamentProgress.setMaximum(300)
                elif temperature['tool0Target'] - temperature['tool0Actual'] > 1:
                    self.changeFilamentProgress.setMaximum(temperature['tool0Target'])
                else:
                    self.changeFilamentProgress.setMaximum(temperature['tool0Actual'])
                    self.changeFilamentHeatingFlag = False
                    if self.loadFlag:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                    else:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                self.changeFilamentProgress.setValue(temperature['tool0Actual'])
            elif self.activeExtruder == 1:
                if temperature['tool1Target'] == 0:
                    self.changeFilamentProgress.setMaximum(300)
                elif temperature['tool1Target'] - temperature['tool1Actual'] > 1:
                    self.changeFilamentProgress.setMaximum(temperature['tool1Target'])
                else:
                    self.changeFilamentProgress.setMaximum(temperature['tool1Actual'])
                    self.changeFilamentHeatingFlag = False
                    if self.loadFlag:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                    else:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                self.changeFilamentProgress.setValue(temperature['tool1Actual'])

    def updatePrintStatus(self, file):
        '''
        displays infromation of a particular file on the home page,is a slot for the signal emited from the thread that keeps pooling for printer status
        runs at 1HZ, so do things that need to be constantly updated only
        :param file: dict of all the attributes of a particualr file
        '''
        if file == None:
            self.currentFile = None
            self.currentImage = None
            self.timeLeft.setText("-")
            self.fileName.setText("-")
            self.printProgressBar.setValue(0)
            self.printTime.setText("-")
            self.playPauseButton.setDisabled(True)  # if file available, make play buttom visible

        else:
            self.playPauseButton.setDisabled(False)  # if file available, make play buttom visible
            self.fileName.setText(file['job']['file']['name'])
            self.currentFile = file['job']['file']['name']
            if file['progress']['printTime'] == None:
                self.printTime.setText("-")
            else:
                m, s = divmod(file['progress']['printTime'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.printTime.setText("%d:%d:%02d:%02d" % (d, h, m, s))

            if file['progress']['printTimeLeft'] == None:
                self.timeLeft.setText("-")
            else:
                m, s = divmod(file['progress']['printTimeLeft'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.timeLeft.setText("%d:%d:%02d:%02d" % (d, h, m, s))

            if file['progress']['completion'] == None:
                self.printProgressBar.setValue(0)
            else:
                self.printProgressBar.setValue(file['progress']['completion'])
                if lightbar and self.setLEDFromStatus:
                    lightbar.write('state:2[' + str(int(file['progress']['completion'])) + ']\n')

            '''
            If image is available from server, set it, otherwise display default image.
            If the image was already loaded, dont load it again.
            '''
            if self.currentImage != self.currentFile:
                self.currentImage = self.currentFile
                img = octopiclient.getImage(file['job']['file']['name'].replace(".gcode", ".png"))
                if img:
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(img)
                    self.printPreviewMain.setPixmap(pixmap)
                else:
                    self.printPreviewMain.setPixmap(QtGui.QPixmap(_fromUtf8("png/printer2.png")))

    def updateStatus(self, status):
        '''
        Updates the status bar, is a slot for the signal emited from the thread that constantly polls for printer status
        this function updates the status bar, as well as enables/disables relavent buttons
        :param status: String of the status text

        '''

        self.printerStatusText = status
        self.printerStatus.setText(status)

        if status == "Printing":  # Green
            self.printerStatusColour.setStyleSheet(_fromUtf8("     border: 1px solid rgb(87, 87, 87);\n"
                                                             "    border-radius: 10px;\n"
                                                             "    background-color: qlineargradient(spread:pad, x1:0, y1:0.523, x2:0, y2:0.534, stop:0 rgba(130, 203, 117, 255), stop:1 rgba(66, 191, 85, 255));"))
        elif status == "Offline":  # Red
            self.printerStatusColour.setStyleSheet(_fromUtf8("     border: 1px solid rgb(87, 87, 87);\n"
                                                             "    border-radius: 10px;\n"
                                                             "background-color: qlineargradient(spread:pad, x1:0, y1:0.517, x2:0, y2:0.512, stop:0 rgba(255, 28, 35, 255), stop:1 rgba(255, 68, 74, 255));"))
            if lightbar and self.setLEDFromStatus:
                lightbar.write('state:4\n')
        elif status == "Paused":  # Amber
            self.printerStatusColour.setStyleSheet(_fromUtf8("     border: 1px solid rgb(87, 87, 87);\n"
                                                             "    border-radius: 10px;\n"
                                                             "background-color: qlineargradient(spread:pad, x1:0, y1:0.523, x2:0, y2:0.54, stop:0 rgba(255, 211, 78, 255), stop:1 rgba(219, 183, 74, 255));"))
            if lightbar and self.setLEDFromStatus:
                lightbar.write('state:3\n')
        elif status == "Operational":  # Amber
            self.printerStatusColour.setStyleSheet(_fromUtf8("     border: 1px solid rgb(87, 87, 87);\n"
                                                             "    border-radius: 10px;\n"
                                                             "background-color: qlineargradient(spread:pad, x1:0, y1:0.523, x2:0, y2:0.54, stop:0 rgba(74, 183, 255, 255), stop:1 rgba(53, 173, 242, 255));"))
            if lightbar and self.setLEDFromStatus:
                lightbar.write('state:1\n')
        '''
        Depending on Status, enable and Disable Buttons
        '''
        if status == "Printing":
            self.playPauseButton.setChecked(True)
            self.stopButton.setDisabled(False)
            self.motionTab.setDisabled(True)
            self.changeFilamentButton.setDisabled(True)
            self.menuCaliberateButton.setDisabled(True)
            self.menuSettingsButton.setDisabled(True)
            self.menuPrintButton.setDisabled(True)


        elif status == "Paused":
            self.playPauseButton.setChecked(False)
            self.stopButton.setDisabled(False)
            self.motionTab.setDisabled(False)
            self.changeFilamentButton.setDisabled(False)
            self.menuCaliberateButton.setDisabled(True)
            self.menuSettingsButton.setDisabled(True)
            self.menuPrintButton.setDisabled(True)


        else:
            self.stopButton.setDisabled(True)
            self.playPauseButton.setChecked(False)
            self.motionTab.setDisabled(False)
            self.changeFilamentButton.setDisabled(False)
            self.menuCaliberateButton.setDisabled(False)
            self.menuSettingsButton.setDisabled(False)
            self.menuPrintButton.setDisabled(False)

    def deleteItem(self):
        '''
        Deletes a gcode file, and if associates, its image file from the memory
        '''
        octopiclient.deleteFile(self.fileListWidget.currentItem().text())
        octopiclient.deleteFile(self.fileListWidget.currentItem().text().replace(".gcode", ".png"))

        # delete PNG also
        self.fileListLocal()

    def playPauseAction(self):
        '''
        Toggles Play/Pause of a print depending on the status of the print
        '''
        if self.printerStatusText == "Operational":
            if self.playPauseButton.isChecked:
                octopiclient.startPrint()
        elif self.printerStatusText == "Printing":
            octopiclient.pausePrint()
            self.activeExtruderPrint = self.activeExtruder

        elif self.printerStatusText == "Paused":
            if self.activeExtruderPrint != self.activeExtruder:  # if the active extruder was chanegd between the print, change it back
                octopiclient.selectTool(self.activeExtruderPrint)
            octopiclient.pausePrint()

    def stopAction(self):
        '''
        Displays a message box asking if the user is sure if he wants to turn off the print
        '''
        choice = QtGui.QMessageBox()
        choice.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        font = QtGui.QFont()
        QtGui.QInputMethodEvent
        font.setFamily(_fromUtf8("Gotham"))
        font.setPointSize(14)
        font.setBold(False)
        font.setUnderline(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        choice.setFont(font)
        choice.setText("Are you sure you want to stop the Print?")
        # choice.setText(text)
        choice.setIconPixmap(QtGui.QPixmap(_fromUtf8("png/exclamation-mark.png")))
        # choice.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        choice.setGeometry(QtCore.QRect(75, 50, 300, 300))
        choice.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        choice.setStyleSheet(_fromUtf8("\n"
                                       "QPushButton{\n"
                                       "     border: 1px solid rgb(87, 87, 87);\n"
                                       "    background-color: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0.188, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(255, 255, 255, 255));\n"
                                       "height:70px;\n"
                                       "width: 150px;\n"
                                       "border-radius:5px;\n"
                                       "    font: 14pt \"Gotham\";\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton:pressed {\n"
                                       "    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,\n"
                                       "                                      stop: 0 #dadbde, stop: 1 #f6f7fa);\n"
                                       "}\n"
                                       "QPushButton:focus {\n"
                                       "outline: none;\n"
                                       "}\n"
                                       "\n"
                                       ""))
        retval = choice.exec_()
        if retval == QtGui.QMessageBox.Yes:
            octopiclient.cancelPrint()

    def selectToolChangeFilament(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        '''

        if self.toolToggleChangeFilamentButton.isChecked():
            self.setActiveExtruder(1)
            octopiclient.selectTool(1)
        else:
            self.setActiveExtruder(0)
            octopiclient.selectTool(0)

    def selectToolMotion(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        '''

        if self.toolToggleMotionButton.isChecked():
            self.setActiveExtruder(1)
            octopiclient.selectTool(1)

        else:
            self.setActiveExtruder(0)
            octopiclient.selectTool(0)

    def selectToolTemperature(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text.it also updates the status of the other toggle buttons
        '''
        self.toolToggleTemperatureButton.setText(
            "1") if self.toolToggleTemperatureButton.isChecked() else self.toolToggleTemperatureButton.setText("0")
        if self.toolToggleTemperatureButton.isChecked():
            print "extruder 1 Temperature"
            self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
        else:
            print "extruder 0 Temperature"
            self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))

    def setStep(self, stepRate):
        '''
        Sets the class variable "Step" which would be needed for movement and joging
        :param step: step multiplier for movement in the move
        :return: nothing

        '''

        if stepRate == 0.1:
            self.step0_1Button.setFlat(True)
            self.step1Button.setFlat(False)
            self.step10Button.setFlat(False)
            self.step = 0.1
        if stepRate == 1:
            self.step0_1Button.setFlat(False)
            self.step1Button.setFlat(True)
            self.step10Button.setFlat(False)
            self.step = 1
        if stepRate == 10:
            self.step0_1Button.setFlat(False)
            self.step1Button.setFlat(False)
            self.step10Button.setFlat(True)
            self.step = 10

    def coolDownAction(self):
        ''''
        Turns all heaters and fans off
        '''
        octopiclient.gcode(command='M107')
        octopiclient.setToolTemperature({"tool0": 0, "tool1": 0})
        # octopiclient.setToolTemperature({"tool0": 0})
        octopiclient.setBedTemperature(0)
        self.toolTempSpinBox.setProperty("value", 0)
        self.bedTempSpinBox.setProperty("value", 0)

    def setActiveExtruder(self, activeNozzle):
        activeNozzle = int(activeNozzle)
        if activeNozzle == 0:
            self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("png/activeNozzle.png")))
            self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("png/Nozzle.png")))
            self.toolToggleChangeFilamentButton.setChecked(False)
            self.toolToggleChangeFilamentButton.setText("0")
            self.toolToggleMotionButton.setChecked(False)
            self.toolToggleMotionButton.setText("0")
            self.activeExtruder = 0
        elif activeNozzle == 1:
            self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("png/Nozzle.png")))
            self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("png/activeNozzle.png")))
            self.toolToggleChangeFilamentButton.setChecked(True)
            self.toolToggleChangeFilamentButton.setText("1")
            self.toolToggleMotionButton.setChecked(True)
            self.toolToggleMotionButton.setText("1")
            self.activeExtruder = 1

            # set button states
            # set octoprint if mismatch

    def setZHomeOffsestUI(self, offset):
        '''
        Sets the spinbox value to have the value of the Z offset from the printer.
        the value is -ve so as to be more intuitive.
        :param offset:
        :return:
        '''
        self.nozzleOffsetDoubleSpinBox.setValue(-float(offset))

    def setZHomeOffset(self, offset, setOffset=False):
        '''
        Sets the home offset after the caliberation wizard is done, which is a callback to
        the response of M114 that is sent at the end of the Wizard in doneStep()
        :param offset: the value off the offset to set. is a str is coming from M114, and is float if coming from the nozzleOffsetPage
        :param setOffset: Boolean, is true if the function call is from the nozzleOFfsetPage
        :return:
        '''
        if self.setHomeOffsetBool:
            octopiclient.gcode(command='M206 Z{}'.format(-float(offset)))
            self.setHomeOffsetBool = False
            octopiclient.gcode(command='M500')
            # sale in EEPROM
        if setOffset:
            octopiclient.gcode(command='M206 Z{}'.format(-offset))
            octopiclient.gcode(command='M500')

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # ++++++++++++++++++++++++Function that change screens++++++++++++++++++++++++++
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def pairPhoneApp(self):
        if self.getIP('eth0') != 'Not Connected':
            qrip = self.getIP('eth0')
        elif self.getIP('wlan0') != 'Not Connected':
            qrip = self.getIP('wlan0')
        else :
            qrip = None
        self.QRCodeLabel.setPixmap(qrcode.make(json.dumps({'apiKey': apiKey, 'IP': qrip}), image_factory = Image).pixmap())
        self.stackedWidget.setCurrentWidget(self.QRCodePage)
    def networkInfo(self):
        self.stackedWidget.setCurrentWidget(self.networkInfoPage)
        self.hostname.setText(subprocess.Popen("cat /etc/hostname", stdout=subprocess.PIPE, shell=True).communicate()[0])
        self.wifiIp.setText(self.getIP('wlan0'))
        self.lanIp.setText(self.getIP('eth0'))

    def getIP(self, interface):
        try:
            scan_result = \
            subprocess.Popen("ifconfig | grep " + interface + " -A 1", stdout=subprocess.PIPE, shell=True).communicate()[0]
            # Processing STDOUT into a dictionary that later will be converted to a json file later
            scan_result = scan_result.split('\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
            scan_result = [s.strip() for s in scan_result]
            # scan_result = [s.strip('"') for s in scan_result]
            scan_result = filter(None, scan_result)
            return scan_result[1][scan_result[1].index('inet addr:') + 10: 23]
        except:
            return "Not Connected"

    def wifiSettings(self):
        self.stackedWidget.setCurrentWidget(self.wifiSettingsPage)
        self.wifiSettingsComboBox.clear()
        self.wifiSettingsComboBox.addItems(self.scan_wifi())

    def restartNetworkingMessageBox(self):
        '''
        Displays a message box for changing network activity
        '''
        self.wifiMessageBox = QtGui.QMessageBox()
        self.wifiMessageBox.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        font = QtGui.QFont()
        QtGui.QInputMethodEvent
        font.setFamily(_fromUtf8("Gotham"))
        font.setPointSize(14)
        font.setBold(False)
        font.setUnderline(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        self.wifiMessageBox.setFont(font)
        self.wifiMessageBox.setText("Restarting networking, please wait...")
        self.wifiMessageBox.setIconPixmap(QtGui.QPixmap(_fromUtf8("png/exclamation-mark.png")))
        # choice.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.wifiMessageBox.setGeometry(QtCore.QRect(110, 50, 200, 300))
        self.wifiMessageBox.setStandardButtons(QtGui.QMessageBox.Cancel)
        self.wifiMessageBox.setStyleSheet(_fromUtf8("\n"
                                       "QMessageBox{\n"
                                       "height:300px;\n"
                                       "width: 400px;\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton{\n"
                                       "     border: 1px solid rgb(87, 87, 87);\n"
                                       "    background-color: qlineargradient(spread:pad, x1:0, y1:1, x2:0, y2:0.188, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(255, 255, 255, 255));\n"
                                       "height:70px;\n"
                                       "width: 150px;\n"
                                       "border-radius:5px;\n"
                                       "    font: 14pt \"Gotham\";\n"
                                       "}\n"
                                       "\n"
                                       "QPushButton:pressed {\n"
                                       "    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,\n"
                                       "                                      stop: 0 #dadbde, stop: 1 #f6f7fa);\n"
                                       "}\n"
                                       "QPushButton:focus {\n"
                                       "outline: none;\n"
                                       "}\n"

                                       "\n"
                                       ""))
        retval = self.wifiMessageBox.exec_()
        if retval == QtGui.QMessageBox.Ok or QtGui.QMessageBox.Cancel:
            self.stackedWidget.setCurrentWidget(self.settingsPage)

    def unloadFilament(self):
        octopiclient.setToolTemperature({"tool1": filaments[str(
            self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
            filaments[str(self.changeFilamentComboBox.currentText())])
        self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
        self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
        self.changeFilamentNameOperation.setText("Unloading {}".format(str(self.changeFilamentComboBox.currentText())))
        # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
        self.changeFilamentHeatingFlag = True
        self.loadFlag = False

    def loadFilament(self):
        octopiclient.setToolTemperature({"tool1": filaments[str(
            self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
            filaments[str(self.changeFilamentComboBox.currentText())])
        self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
        self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
        self.changeFilamentNameOperation.setText("Loading {}".format(str(self.changeFilamentComboBox.currentText())))
        # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
        self.changeFilamentHeatingFlag = True
        self.loadFlag = True

    def changeFilament(self):
        self.stackedWidget.setCurrentWidget(self.changeFilamentPage)
        self.changeFilamentComboBox.clear()
        self.changeFilamentComboBox.addItems(filaments.keys())

    def changeFilamentCancel(self):
        self.changeFilamentHeatingFlag = False
        self.coolDownAction()
        self.stackedWidget.setCurrentWidget(self.controlPage)

    def fileListLocal(self):
        '''
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page
        '''
        self.stackedWidget.setCurrentWidget(self.fileListLocalPage)
        files = octopiclient.retrieveFileInformation()['files']

        for file in files:
            if file["type"] != "machinecode":
                files.remove(file)

        self.fileListWidget.clear()
        files.sort(key=lambda d: d['date'], reverse=True)
        # for item in [f['name'] for f in files] :
        #     self.fileListWidget.addItem(item)
        self.fileListWidget.addItems([f['name'] for f in files])
        self.fileListWidget.setCurrentRow(0)

    def fileListUSB(self):
        '''
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page

        ToDO: Add deapth of folders recursively get all gcodes
        '''
        self.stackedWidget.setCurrentWidget(self.fileListUSBPage)
        self.fileListWidgetUSB.clear()
        files = subprocess.Popen("ls /media/usb0 | grep gcode", stdout=subprocess.PIPE, shell=True).communicate()[0]
        files = files.split('\n')
        files = filter(None, files)
        # for item in files:
        #     self.fileListWidgetUSB.addItem(item)
        self.fileListWidgetUSB.addItems(files)
        self.fileListWidgetUSB.setCurrentRow(0)

    def printSelectedLocal(self):

        '''
        gets information about the selected file from octoprint server,
        as well as sets the current page to the print selected page.

        This function also selects the file to print from octoprint
        '''
        try:
            self.fileSelected.setText(self.fileListWidget.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)
            file = octopiclient.retrieveFileInformation(self.fileListWidget.currentItem().text())
            try:
                self.fileSizeSelected.setText(size(file['size']))
            except KeyError:
                self.fileSizeSelected.setText('-')
            try:
                self.fileDateSelected.setText(datetime.fromtimestamp(file['date']).strftime('%d/%m/%Y %H:%M:%S'))
            except KeyError:
                self.fileDateSelected.setText('-')
            try:
                m, s = divmod(file['gcodeAnalysis']['estimatedPrintTime'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.filePrintTimeSelected.setText("%dd:%dh:%02dm:%02ds" % (d, h, m, s))
            except KeyError:
                self.filePrintTimeSelected.setText('-')
            try:
                self.filamentVolumeSelected.setText(
                    ("%.2f cm" % file['gcodeAnalysis']['filament']['tool0']['volume']) + unichr(179))
            except KeyError:
                self.filamentVolumeSelected.setText('-')

            try:
                self.filamentLengthFileSelected.setText(
                    "%.2f mm" % file['gcodeAnalysis']['filament']['tool0']['length'])
            except KeyError:
                self.filamentLengthFileSelected.setText('-')
            # uncomment to select the file when selectedd in list
            # octopiclient.selectFile(self.fileListWidget.currentItem().text(), False)
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)

            '''
            If image is available from server, set it, otherwise display default image
            '''
            img = octopiclient.getImage(self.fileListWidget.currentItem().text().replace(".gcode", ".png"))
            if img:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(img)
                self.printPreviewSelected.setPixmap(pixmap)

            else:
                self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("png/printer2.png")))


        except:
            print "Log: Nothing Selected"



            # Set image fot print preview:
            # self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("png/fracktal.png")))
            # print self.fileListWidget.currentItem().text().replace(".gcode","")
            # self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("/home/pi/.octoprint/uploads/{}.png".format(self.FileListWidget.currentItem().text().replace(".gcode","")))))

            # Check if the PNG file exists, and if it does display it, or diplay a default picture.

    def printSelectedUSB(self):
        '''
        Sets the screen to the print selected screen for USB, on which you can transfer to local drive and view preview image.
        :return:
        '''
        try:
            self.fileSelectedUSBName.setText(self.fileListWidgetUSB.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedUSBPage)
            file = '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text().replace(".gcode", ".png"))
            try:
                exists = os.path.exists(file)
            except:
                exists = False

            if exists:
                self.printPreviewSelectedUSB.setPixmap(QtGui.QPixmap(_fromUtf8(file)))
            else:
                self.printPreviewSelectedUSB.setPixmap(QtGui.QPixmap(_fromUtf8("png/printer2.png")))
        except:
            print "Log: Nothing Selected"

            # Set Image from USB

    def transferToLocal(self, prnt=False):
        '''
        Transfers a file from USB mounted at /media/usb0 to octoprint's watched folder so that it gets automatically detected bu Octoprint.
        Warning: If the file is read-only, octoprint API for reading the file crashes.
        '''

        file = '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text())

        self.uploadThread = fileUploadThread(file, prnt=prnt)
        self.uploadThread.start()
        if prnt:
            self.stackedWidget.setCurrentWidget(self.homePage)

    def printFile(self):
        '''
        Prints the file selected from printSelected()
        '''
        octopiclient.selectFile(self.fileListWidget.currentItem().text(), True)
        # octopiclient.startPrint()
        self.stackedWidget.setCurrentWidget(self.homePage)

    def control(self):
        self.stackedWidget.setCurrentWidget(self.controlPage)
        if self.toolToggleTemperatureButton.isChecked():
            self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
        else:
            self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))
        self.bedTempSpinBox.setProperty("value", float(self.bedTargetTemperature.text()))

    def nozzleOffset(self):
        octopiclient.gcode(command='M503')
        self.stackedWidget.setCurrentWidget(self.nozzleOffsetPage)

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # ++++++++++++++++++++++++++++++Caliberation Wizzard++++++++++++++++++++++++++++
    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    def step1(self):
        '''
        Shows welcome message.
        Sets Z Home Offset = 0
        Homes to MAX
        MOves to X=MAX/2, Y=MAX/2, Z=35
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.step1Page)
        octopiclient.gcode(command='M206 Z0')
        octopiclient.home(['x', 'y', 'z'])
        octopiclient.jog(x=125, y=125, z=35, absolute=True, speed=1500)
        self.setLEDFromStatus = False  # so that led is updated from ui, not from octoptint loop
        if lightbar:
            lightbar.write('state:5\n')

    def step2(self):
        '''
        Askes user to release all Leveling Screws
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.step2Page)
        self.movie1.start()

    def step3(self):
        '''
        Goes to first Leveling point, and goes to Z=0
        Then asks user to tighten right leveling screw
        '''
        self.stackedWidget.setCurrentWidget(self.step3Page)
        octopiclient.jog(x=246.13, y=22.0, absolute=True)
        octopiclient.jog(z=0, absolute=True)

        self.movie1.stop()

        self.movie2.start()

    def step4(self):
        '''
        Z=5, then go to left leveling position, then z=0
        Then asks user to tighten left leveling screw
        :return:
        '''
        # sent twice for some reason
        self.stackedWidget.setCurrentWidget(self.step4Page)
        octopiclient.jog(z=10, absolute=True)
        octopiclient.jog(x=56.76, y=22, absolute=True)
        octopiclient.jog(z=0, absolute=True)
        self.movie2.stop()

        self.movie3.start()

    def step5(self):
        '''
        Z=5, then go to center leveling position, then z=0
        Then asks user to tighten center leveling screw
        :return:
        '''
        # sent twice for some reason
        self.stackedWidget.setCurrentWidget(self.step5Page)
        octopiclient.jog(z=10, absolute=True)
        octopiclient.jog(x=142.45, y=186.94, absolute=True)
        octopiclient.jog(z=0, absolute=True)
        self.movie3.stop()

        self.movie4.start()

    def step6(self):
        '''
        sets z = 5, goes to front position for nozzle height adjustment, then sets z=2
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.step6Page)
        octopiclient.jog(z=10, absolute=True)
        octopiclient.jog(x=142, y=188, absolute=True)
        octopiclient.jog(z=2, absolute=True)
        self.movie4.stop()

    def step7(self):
        '''
        Shows the animaion to show how leveling is done
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.step7Page)

        self.movie5.start()

    def step8(self):
        '''
        actually jogs the nozzle up depending on user input by a factor of 0.05
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.step8Page)
        self.movie5.stop()
        # Jog commads are set in setActions() under caliberation

    def doneStep(self):
        '''
        Sets the new z home offset, and goes back to caliebration page
        :return:
        '''
        self.setLEDFromStatus = True
        self.stackedWidget.setCurrentWidget(self.caliberatePage)
        self.setHomeOffsetBool = True
        octopiclient.gcode(command='M114')
        # set current Z value as -home offset

    def cancelStep(self):
        self.setLEDFromStatus = True
        self.movie1.stop()
        self.movie2.stop()
        self.movie3.stop()
        self.movie4.stop()
        self.movie5.stop()
        self.stackedWidget.setCurrentWidget(self.caliberatePage)


class QtWebsocket(QtCore.QThread):
    '''
    https://pypi.python.org/pypi/websocket-client
    https://wiki.python.org/moin/PyQt/Threading,_Signals_and_Slots
    '''

    def __init__(self):
        super(QtWebsocket, self).__init__()

        url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(
            ip,  # host + port + prefix, but no protocol
            random.randrange(0, stop=999),  # server_id
            uuid.uuid4()  # session_id
        )
        self.ws = websocket.WebSocketApp(url,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)

    def run(self):
        self.ws.run_forever()

    def on_message(self, ws, message):

        message_type = message[0]
        if message_type == "h":
            # "heartbeat" message
            return
        elif message_type == "o":
            # "open" message
            return
        elif message_type == "c":
            # "close" message
            return

        message_body = message[1:]
        if not message_body:
            return
        data = json.loads(message_body)[0]

        if message_type == "m":
            data = [data, ]

        if message_type == "a":
            self.process(data)

    @run_async
    def process(self, data):
        if "plugin" in data:
            if data["plugin"]["plugin"] == 'Julia3GFilament':
                if data["plugin"]["data"]["status_value"] == 'error':
                    self.emit(QtCore.SIGNAL('FILAMENT_SENSOR_TRIGGERED'))

        if "current" in data:

            if data["current"]["messages"]:
                for item in data["current"]["messages"]:
                    if 'Active Extruder' in item:
                        self.emit(QtCore.SIGNAL('ACTIVE_EXTRUDER'), item[-1])
                    if 'M206' in item:
                        self.emit(QtCore.SIGNAL('Z_HOME_OFFSET'), item[item.index('Z') + 1:])
                    if 'Count' in item:
                        index = item.index('Z')
                        self.emit(QtCore.SIGNAL('SET_Z_HOME_OFFSET'), item[index + 2:index + 7], False)

            if data["current"]["state"]["text"]:
                self.emit(QtCore.SIGNAL('STATUS'), data["current"]["state"]["text"])

            fileInfo = {"job": data["current"]["job"], "progress": data["current"]["progress"]}
            if fileInfo['job']['file']['name'] != None:
                self.emit(QtCore.SIGNAL('PRINT_STATUS'), fileInfo)
            else:
                self.emit(QtCore.SIGNAL('PRINT_STATUS'), None)

            if data["current"]["temps"]:
                if data["current"]["temps"][0]["tool1"]["actual"] == None:
                    data["current"]["temps"][0]["tool1"]["actual"] = 0
                temperatures = {'tool0Actual': data["current"]["temps"][0]["tool0"]["actual"],
                                'tool0Target': data["current"]["temps"][0]["tool0"]["target"],
                                'tool1Actual': data["current"]["temps"][0]["tool1"]["actual"],
                                'tool1Target': data["current"]["temps"][0]["tool1"]["target"],
                                'bedActual': data["current"]["temps"][0]["bed"]["actual"],
                                'bedTarget': data["current"]["temps"][0]["bed"]["target"]}
                self.emit(QtCore.SIGNAL('TEMPERATURES'), temperatures)

    def on_open(self, ws):
        pass

    def on_close(self, ws):
        pass

    def on_error(self, ws, error):
        pass


class sanityCheckThread(QtCore.QThread):
    def __init__(self):
        super(sanityCheckThread, self).__init__()
        self.MKSPort = None
        self.lightBarPort = None

    def run(self):
        global octopiclient
        global lightbar
        # keep trying untill octoprint connects
        while (True):
            # Start an object instance of octopiAPI
            try:
                octopiclient = octoprintAPI(ip, apiKey)
                result = subprocess.Popen("dmesg | grep 'ttyUSB'", stdout=subprocess.PIPE, shell=True).communicate()[0]
                result = result.split('\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
                result = [s.strip() for s in result]
                for line in result:
                    if 'FTDI' in line:
                        self.MKSPort = line[line.index('ttyUSB'):line.index('ttyUSB') + 7]
                    elif 'ch341-uart' in line:
                        self.lightBarPort = line[line.index('ttyUSB'):line.index('ttyUSB') + 7]

                if not self.MKSPort:
                    octopiclient.connectPrinter(port="VIRTUAL", baudrate=115200)
                else:
                    octopiclient.connectPrinter(port="/dev/" + self.MKSPort, baudrate=115200)
                break
            except:
                time.sleep(1)
                print "Not Connected!"
        self.emit(QtCore.SIGNAL('LOADED'))
        if self.lightBarPort:
            lightbar = serial.Serial(port="/dev/" + self.lightBarPort, baudrate=9600)
            time.sleep(2)
            lightbar.write('state:1\n')
        else:
            lightbar = False


class fileUploadThread(QtCore.QThread):
    def __init__(self, file, prnt=False):
        super(fileUploadThread, self).__init__()
        self.file = file
        self.prnt = prnt

    def run(self):

        try:
            exists = os.path.exists(self.file.replace(".gcode", ".png"))
        except:
            exists = False
        if exists:
            octopiclient.uploadImage(self.file.replace(".gcode", ".png"))

        if self.prnt:
            octopiclient.uploadGcode(file=self.file, select=True, prnt=True)
        else:
            octopiclient.uploadGcode(file=self.file, select=False, prnt=False)


class restartNetworkingThread(QtCore.QThread):
    def __init__(self):
        super(restartNetworkingThread, self).__init__()

    def run(self):
        self.restart_wlan0()
        attempt = 0
        while attempt < 3:
            if self.getIP():
                self.emit(QtCore.SIGNAL('IP_ADDRESS'), self.getIP())
                break
            else:
                attempt += 1
                time.sleep(1)
        if attempt >= 3:
            self.emit(QtCore.SIGNAL('IP_ADDRESS'), None)


    def restart_wlan0(self):
        '''
        restars wlan0 wireless interface to use new changes in wpa_supplicant.conf file
        :return:
        '''
        subprocess.call(["ifdown", "--force", "wlan0"], shell=False)
        subprocess.call(["ifup", "--force", "wlan0"], shell=False)
        time.sleep(5)

    def getIP(self):
        try:
            scan_result = \
            subprocess.Popen("ifconfig | grep wlan0 -A 1", stdout=subprocess.PIPE, shell=True).communicate()[0]
            # Processing STDOUT into a dictionary that later will be converted to a json file later
            scan_result = scan_result.split('\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
            scan_result = [s.strip() for s in scan_result]
            # scan_result = [s.strip('"') for s in scan_result]
            scan_result = filter(None, scan_result)
            return scan_result[1][scan_result[1].index('inet addr:') + 10: 23]
        except:
            return None


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    # Intialize the library (must be called once before other functions).
    # Creates an object of type MainUiClass
    MainWindow = MainUiClass()
    MainWindow.show()
    # MainWindow.showFullScreen()
    # MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    # Create NeoPixel object with appropriate configuration.
    # charm = FlickCharm()
    # charm.activateOn(MainWindow.FileListWidget)
    sys.exit(app.exec_())
