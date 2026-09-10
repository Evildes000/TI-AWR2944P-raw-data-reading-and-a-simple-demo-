# TI-AWR2944P-raw-data-reading-and-a-simple-demo-


# DataCapture_AWR2944P.lua 
is a lua file which can be used to configure AWR2944p automatically. Because AWR2944p is a brand new version of TI mmWave radar and there is almost no such lua file to configrue the radar, so this lua script is quite meaningfull as it can make radar confiuration more convenient. 

# RadarConfigure.m
Start mmWave Studio and load the lua file to it

# SendCaptureCMD.m
After run RadarConfig.m, run SendCaptureCMD.m to trigger frame


# MyRawDataReader.m 
an example of how to read the raw binary data recorded by AWR2944P and transfer it to a available datacube with the shape [numChirpPerFrame, numSamplesPerChirp, numFrame, numRx]


# AUTO_CAPTURE.lua
If you don't want to excuate so many befor-mentioned files, then load and run this lua file in mmWave Studio. It will configure all paranmeters automatically. After load this file, you may change some parameters value by you self. For example, in our experiment, change following parameters in SensroConfig tag to corresponding valus: <br>
Profile:
      Start Freq --> 76.50 <br>
      Frequency Slop --> 112.009 <br>
      Idle Time --> 5.00 <br>
      ADC samples --> 256 <br>
      Sample Rate --> 8000 <br>
      Ramp End Time --> 40.00 <br>
      RX Gain --> 45 <br>
      RF Gain Traget --> 34 dB <br>
      VCO Select --> VCO2 <br>
Frame；<br>
      No of Chirp Loops --> 128 <br>
      Start Chirp TX --> 0 <br>
      End Chirp TX --> 0 <br>
      No of Frame --> depneds <br>
      Periodicity --> depneds <br>

Attention: Idle Time + Ramp End Time = chirp duration, Periodicity must larger  (than No of Chirp Loops * chirp duration)



