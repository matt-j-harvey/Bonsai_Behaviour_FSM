from PyDAQmx import DAQmxTypes, DAQmxConstants, DAQmxFunctions, DAQmxCallBack
import numpy as np
import os
import pyqtgraph as pg
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import sys
import tables
import threading
import time

global recording
global daq_1_display_buffer
global daq_2_display_buffer

from wakepy import keep

daq_1_display_buffer = np.zeros((8,5000))
daq_2_display_buffer = np.zeros((8,5000))
recording = False

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

class ai_window(QWidget):

    def __init__(self,parent=None):
        super(ai_window, self).__init__(parent)


        #Setup Window
        self.setWindowTitle("PyI Recorder")
        self.setGeometry(0,0,450,900)
        self.setStyleSheet("background-color: white;")
        self.pen = pg.mkPen(color=(100, 100, 200), width=2)
        self.save_directory = "C:\Behavioural_data"

        # Create Graph Displays
        self.graphics_widget_layout = pg.GraphicsLayoutWidget()



        self.graph_7_widget = self.graphics_widget_layout.addPlot(row=0, col=0)
        self.graph_7_widget.setYRange(0, 6)
        self.graph_7_widget.getAxis('left').setWidth(15)
        self.graph_7_widget.setTitle("Running")

        self.graph_4_widget = self.graphics_widget_layout.addPlot(row=1, col=0)
        self.graph_4_widget.setYRange(0,6)
        self.graph_4_widget.getAxis('left').setWidth(15)
        self.graph_4_widget.setTitle("Trial Start")

        self.graph_1_widget = self.graphics_widget_layout.addPlot(row=2, col=0)
        self.graph_1_widget.setYRange(0,6)
        self.graph_1_widget.getAxis('left').setWidth(15)
        self.graph_1_widget.setTitle("Static Onset")

        self.graph_6_widget = self.graphics_widget_layout.addPlot(row=3, col=0)
        self.graph_6_widget.setYRange(0, 6)
        self.graph_6_widget.getAxis('left').setWidth(15)
        self.graph_6_widget.setTitle("Stop Tone")

        self.graph_5_widget = self.graphics_widget_layout.addPlot(row=4, col=0)
        self.graph_5_widget.setYRange(0,6)
        self.graph_5_widget.getAxis('left').setWidth(15)
        self.graph_5_widget.setTitle("Drift Onset")

        self.graph_3_widget = self.graphics_widget_layout.addPlot(row=5, col=0)
        self.graph_3_widget.setYRange(0,6)
        self.graph_3_widget.getAxis('left').setWidth(15)
        self.graph_3_widget.setTitle("Lick")


        self.graph_0_widget = self.graphics_widget_layout.addPlot(row=6, col=0)
        self.graph_0_widget.setYRange(0,6)
        self.graph_0_widget.getAxis('left').setWidth(15)
        self.graph_0_widget.setTitle("Reward")


        self.graph_2_widget = self.graphics_widget_layout.addPlot(row=7, col=0)
        self.graph_2_widget.setYRange(0,6)
        self.graph_2_widget.getAxis('left').setWidth(15)
        self.graph_2_widget.setTitle("Trial End")



        # Daq 2 Graphs
        self.graph_9_widget = self.graphics_widget_layout.addPlot(row=0, col=1)
        self.graph_9_widget.setYRange(0, 6)
        self.graph_9_widget.getAxis('left').setWidth(15)
        self.graph_9_widget.setTitle("Back Drift Onset")

        self.graph_8_widget = self.graphics_widget_layout.addPlot(row=1, col=1)
        self.graph_8_widget.setYRange(0, 6)
        self.graph_8_widget.getAxis('left').setWidth(15)
        self.graph_8_widget.setTitle("Trial Start")

        self.graph_10_widget = self.graphics_widget_layout.addPlot(row=2, col=1)
        self.graph_10_widget.setYRange(0, 6, padding=0)
        self.graph_10_widget.getAxis('left').setWidth(15)
        self.graph_10_widget.setTitle("Trial Code")

        self.graph_11_widget = self.graphics_widget_layout.addPlot(row=3, col=1)
        self.graph_11_widget.setYRange(-1, 6, padding=0)
        self.graph_11_widget.getAxis('left').setWidth(15)
        self.graph_11_widget.setTitle("Camera")

        self.graph_12_widget = self.graphics_widget_layout.addPlot(row=4, col=1)
        self.graph_12_widget.setYRange(-2, 2, padding=0)
        self.graph_12_widget.getAxis('left').setWidth(15)
        self.graph_12_widget.setTitle("Microphone")

        self.graph_13_widget = self.graphics_widget_layout.addPlot(row=5, col=1)
        self.graph_13_widget.setYRange(0, 6, padding=0)
        self.graph_13_widget.getAxis('left').setWidth(15)
        self.graph_13_widget.setTitle("Photodiode")

        self.graph_15_widget = self.graphics_widget_layout.addPlot(row=6, col=1)
        self.graph_15_widget.setYRange(0, 6)
        self.graph_15_widget.getAxis('left').setWidth(15)
        self.graph_15_widget.setTitle("Optogenetics")
        self.graph_14_widget = self.graphics_widget_layout.addPlot(row=7, col=1)

        self.graph_14_widget.setYRange(0, 6)
        self.graph_14_widget.getAxis('left').setWidth(15)
        self.graph_14_widget.setTitle("Trial End")

        #Create Start Stop Buttons
        self.recording_state = False
        self.recording_button = QPushButton("Start Recording")
        self.recording_button.clicked.connect(self.toggle_recording)

        #Create Directory Selection Button
        self.directory_selection_button = QPushButton("Select Save Directory")
        self.directory_selection_button.clicked.connect(self.select_save_directory)

        #Create Recording Location Label
        self.save_directory_label = QLabel(str(self.save_directory))
        self.save_directory_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        # Create Timer To Update Display
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_display)
        self.timer.start()

        #Add Widgets To Layout




        self.main_layout = QGridLayout()
        self.main_layout.addWidget(self.graphics_widget_layout, 0, 0, 1, 2)


        self.main_layout.addWidget(self.save_directory_label,           24, 0, 1, 4)
        self.main_layout.addWidget(self.recording_button,               25, 0, 1, 4)
        self.main_layout.addWidget(self.directory_selection_button,     26, 0, 1, 4)

        self.setLayout(self.main_layout)

    def toggle_recording(self):

        if self.recording_state == False:
            self.start_recording()
        elif self.recording_state == True:
            self.stop_recording()


    def start_recording(self):
        global recording
        global daq_1_storage_file
        global daq_2_storage_file
        global daq_1_data_storage
        global daq_2_data_storage


        self.recording_button.setText("Stop Recording")
        self.recording_state = True


        # Get Timestamps
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Create Filepaths for Data Files
        daq_1_storage_path = os.path.join(self.save_directory, timestamp + "_daq_1.h5")
        daq_2_storage_path = os.path.join(self.save_directory, timestamp + "_daq_2.h5")
        print("daq_1_storage_path", daq_1_storage_path)
        print("daq_2_storage_path", daq_2_storage_path)

        # Create File Objects
        dimensions = (0, 8, 1000)
        daq_1_storage_file = tables.open_file(daq_1_storage_path, mode='w')
        daq_2_storage_file = tables.open_file(daq_2_storage_path, mode='w')
        daq_1_data_storage = daq_1_storage_file.create_earray(daq_1_storage_file.root, 'Data', tables.Float64Atom(), shape=dimensions)
        daq_2_data_storage = daq_2_storage_file.create_earray(daq_2_storage_file.root, 'Data', tables.Float64Atom(), shape=dimensions)

        # Set Recording Status To True
        recording = True

    def stop_recording(self):
        global recording
        global daq_1_storage_file
        global daq_2_storage_file

        self.recording_state = False
        self.recording_button.setText("Start Recording")
        recording = False
        daq_1_storage_file.close()
        daq_2_storage_file.close()

    def select_save_directory(self):
        self.save_directory = QFileDialog.getExistingDirectory()
        self.save_directory_label.setText(str(self.save_directory))

    def update_display(self):
        global display_buffer

        # DAQ 1 Graphs
        self.graph_0_widget.clear()
        self.graph_0_widget.plot(daq_1_display_buffer[0], pen=self.pen)

        self.graph_1_widget.clear()
        self.graph_1_widget.plot(daq_1_display_buffer[1], pen=self.pen)

        self.graph_2_widget.clear()
        self.graph_2_widget.plot(daq_1_display_buffer[2], pen=self.pen)

        self.graph_3_widget.clear()
        self.graph_3_widget.plot(daq_1_display_buffer[3], pen=self.pen)

        self.graph_4_widget.clear()
        self.graph_4_widget.plot(daq_1_display_buffer[4], pen=self.pen)

        self.graph_5_widget.clear()
        self.graph_5_widget.plot(daq_1_display_buffer[5], pen=self.pen)

        self.graph_6_widget.clear()
        self.graph_6_widget.plot(daq_1_display_buffer[6], pen=self.pen)

        self.graph_7_widget.clear()
        self.graph_7_widget.plot(daq_1_display_buffer[7], pen=self.pen)


        # DAQ 2 Graphs
        self.graph_8_widget.clear()
        self.graph_8_widget.plot(daq_2_display_buffer[0], pen=self.pen)

        self.graph_9_widget.clear()
        self.graph_9_widget.plot(daq_2_display_buffer[1], pen=self.pen)

        self.graph_10_widget.clear()
        self.graph_10_widget.plot(daq_2_display_buffer[2], pen=self.pen)

        self.graph_11_widget.clear()
        self.graph_11_widget.plot(daq_2_display_buffer[3], pen=self.pen)

        self.graph_12_widget.clear()
        self.graph_12_widget.plot(daq_2_display_buffer[4], pen=self.pen)

        self.graph_13_widget.clear()
        self.graph_13_widget.plot(daq_2_display_buffer[5], pen=self.pen)

        self.graph_14_widget.clear()
        self.graph_14_widget.plot(daq_2_display_buffer[6], pen=self.pen)

        self.graph_15_widget.clear()
        self.graph_15_widget.plot(daq_2_display_buffer[7], pen=self.pen)

        app.processEvents()


class MyList(list):
    pass


def daq_1_EveryNCallback_py(taskHandle, everyNsamplesEventType, nSamples, callbackData_ptr):
    global  daq_1_display_buffer

    # Create An Integer Varaible to Store How Many Data Points Have Been Read
    read =  DAQmxTypes.int32()

    # Create A Numpy Array To Store The Read Data
    data = np.zeros(8000)

    # Read Data
    DAQmxFunctions.DAQmxReadAnalogF64(taskHandle,1000,10.0,DAQmxConstants.DAQmx_Val_GroupByChannel,data,8000,DAQmxTypes.byref(read),None)

    # Reshape Into Seperate Channels
    data = np.reshape(data, (8,1000))

    # Add To Display Buffer
    daq_1_display_buffer = np.roll(daq_1_display_buffer, -1000, axis=1)
    daq_1_display_buffer[:, 4000:] = data

    # If We're Recording add it to the H5 File
    if recording == True:
        daq_1_data_storage.append([data])
        daq_1_data_storage.flush()

    # The function should return an integer
    return 0


def daq_2_EveryNCallback_py(taskHandle, everyNsamplesEventType, nSamples, callbackData_ptr):
    global  daq_2_display_buffer

    # Create An Integer Varaible to Store How Many Data Points Have Been Read
    read = DAQmxTypes.int32()

    # Create A Numpy Array To Store The Read Data
    data = np.zeros(8000)

    # Read Data
    DAQmxFunctions.DAQmxReadAnalogF64(taskHandle, 1000, 10.0, DAQmxConstants.DAQmx_Val_GroupByChannel, data, 8000, DAQmxTypes.byref(read), None)

    # Reshape Into Seperate Channels
    data = np.reshape(data, (8, 1000))

    # Add To Display Buffer
    daq_2_display_buffer = np.roll(daq_2_display_buffer, -1000, axis=1)
    daq_2_display_buffer[:, 4000:] = data

    # If We're Recording add it to the H5 File
    if recording == True:
        daq_2_data_storage.append([data])
        daq_2_data_storage.flush()

    # The function should return an integer
    return 0




if __name__ == '__main__':

    with keep.presenting():
        app = QApplication(sys.argv)


        x = np.arange(5000)
        device_names = ["Dev1", "Dev2"]

        window_instance = ai_window()
        window_instance.show()

        # list where the data are stored
        data = MyList()
        id_data = DAQmxCallBack.create_callbackdata_id(data)
        count = 0

        # Convert the python function to a C function callback
        daq_1_EveryNCallback = DAQmxTypes.DAQmxEveryNSamplesEventCallbackPtr(daq_1_EveryNCallback_py)
        daq_2_EveryNCallback = DAQmxTypes.DAQmxEveryNSamplesEventCallbackPtr(daq_2_EveryNCallback_py)

        #Create Task
        taskHandle_daq_1 = DAQmxTypes.TaskHandle(0)                               #Create A Task Handle
        taskHandle_daq_2 = DAQmxTypes.TaskHandle(0)
        DAQmxFunctions.DAQmxCreateTask("", DAQmxTypes.byref(taskHandle_daq_1))    #Create A Task Using This Handle
        DAQmxFunctions.DAQmxCreateTask("", DAQmxTypes.byref(taskHandle_daq_2))    #Create A Task Using This Handle

        # Setup Channels DAQ 1
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai0",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai1",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai2",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai3",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai4",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai5",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai6",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_1, device_names[0] + "/ai7",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)

        # Setup Channels DAQ 1
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai0",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai1",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai2",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai3",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai4",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai5",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai6",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)
        DAQmxFunctions.DAQmxCreateAIVoltageChan(taskHandle_daq_2, device_names[1] + "/ai7",  "", DAQmxConstants.DAQmx_Val_RSE, -10.0,   10.0, DAQmxConstants.DAQmx_Val_Volts, None)

        # Set Clock Timings
        DAQmxFunctions.DAQmxCfgSampClkTiming(taskHandle_daq_1, "", 1000.0, DAQmxConstants.DAQmx_Val_Rising, DAQmxConstants.DAQmx_Val_ContSamps, 1000)
        DAQmxFunctions.DAQmxCfgSampClkTiming(taskHandle_daq_2, "", 1000.0, DAQmxConstants.DAQmx_Val_Rising, DAQmxConstants.DAQmx_Val_ContSamps, 1000)

        # Set Function For Callback
        DAQmxFunctions.DAQmxRegisterEveryNSamplesEvent(taskHandle_daq_1, DAQmxConstants.DAQmx_Val_Acquired_Into_Buffer, 1000, 0, daq_1_EveryNCallback, id_data)
        DAQmxFunctions.DAQmxRegisterEveryNSamplesEvent(taskHandle_daq_2, DAQmxConstants.DAQmx_Val_Acquired_Into_Buffer, 1000, 0, daq_2_EveryNCallback, id_data)

        # DAQmx Start Code
        DAQmxFunctions.DAQmxStartTask(taskHandle_daq_1)
        DAQmxFunctions.DAQmxStartTask(taskHandle_daq_2)


        sys.exit(app.exec_())

