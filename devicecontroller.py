import sounddevice
import threading
import audioop
import numpy as np

duration = 5 # seconds

class device:
    def __init__(self, deviceInfo, id):
        self.active = True
        self.volume = 1;

        self.id = id
        self.name = deviceInfo['name'];
        self.hostapi = deviceInfo['hostapi']
        self.maxInputChannels = deviceInfo['max_input_channels']
        self.maxOutputChannels = deviceInfo['max_output_channels']
        self.defaultLowOutputLatency = deviceInfo['default_low_output_latency']
        self.defaultHighOutputLatency = deviceInfo['default_high_output_latency']
        self.defaultLowInputLatency = deviceInfo['default_low_input_latency']
        self.defaultHighInputLatency = deviceInfo['default_high_input_latency']
        self.defaultSamplerate = deviceInfo['default_samplerate']

        self.rawStream = sounddevice.RawStream()
        self.currRawData = []

    # audio callback
    def callback(self, indata, outdata, frames, time, status):
        if self.active:
            outdata[:] = indata * self.volume;
        else:
            outdata.fill(0)

        self.currRawData = outdata

        if status:
            print("[%s] frames: %s, status: %s" %(self.name, frames, time, status))

    # get average of waveform at current time
    def getDeviceAvg(self):
        return audioop.avg(self.currRawData, 1)

    def stream(self, out):
        try:
            sounddevice.default.channels = out.maxOutputChannels
            self.rawStream = sounddevice.Stream(device=(self.id, out.id), samplerate=self.defaultSamplerate, channels=(self.maxInputChannels, out.maxOutputChannels), callback=self.callback, latency="low")
            self.rawStream.start()
        except sounddevice.PortAudioError as e:
            print("Port audio error for (" + self.name + ") " + str(e))

    # start a sounddevice stream in a new thread (this might not be needed anymore)
    def startStream(self, out):
        threading.Thread(target=self.stream, args=(out,)).start()

    def getType(self):
        if (self.maxOutputChannels > 0):
            return "output"
        else:
            return "input"

# A controller for all devices
class DeviceController:
    def __init__(self):

        self.deviceList = []
        self.activeDevices = []

        self.outputDevice = []

        self.initDevices()

    def initDevices(self):
        id = 0
        for dev in sounddevice.query_devices():
            print(str(id) + " " + str(dev))
            self.deviceList.append(device(dev, id))
            id += 1

    def enableDevice(self, id):
        devList = [d for d in self.deviceList if d.id == id and d.getType() == "input"]
        for dev in devList:
            print(dev.name + "device enabled")
            self.activeDevices.append(dev)
            dev.startStream(self.outputDevice)

    def disableDevice(self, id):
        devList = [d for d in self.activeDevices if d.id == id]
        for dev in devList:
            self.activeDevices.remove(dev)

    def getDevice(self, id):
        return [d for d in self.deviceList if d.id == id]

    def setOutputDevice(self, id):
        devList = [d for d in self.deviceList if d.id == id and d.getType() == "output"]
        if (devList):
            print(devList[0].name + " set to output device")
            self.outputDevice = devList[0]
        else:
            print("[error] id " + id + " not found, output device not set")

    def getTotalCpuLoad(self):
        totalCpu = 0
        for dev in self.activeDevices:
            if dev.active:
                totalCpu += dev.rawStream.cpu_load
        return totalCpu

    # TODO average instead of additive
    def getTotalLatency(self):
        totalLat = 0
        for dev in self.activeDevices:
            if dev.active:
                totalLat += dev.rawStream.latency()
        return totalLat