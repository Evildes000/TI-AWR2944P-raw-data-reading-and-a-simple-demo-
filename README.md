# TI-AWR2944P-raw-data-reading-and-a-simple-demo-


# DataCapture_AWR2944P.lua 
is a lua file which can be used to configure AWR2944p automatically. Because AWR2944p is a brand new version of TI mmWave radar and there is almost no such lua file to configrue the radar, so this lua script is quite meaningfull as it can make radar confiuration more convenient. 

# RadarConfigure.m
Start mmWave Studio and load the lua file to it

# SendCaptureCMD.m
After run RadarConfig.m, run SendCaptureCMD.m to trigger frame


# MyRawDataReader.m 
an example of how to read the raw binary data recorded by AWR2944P and transfer it to a available datacube with the shape [numChirpPerFrame, numSamplesPerChirp, numFrame, numRx]
