clc
clear all
close all

path_to_setupjsonfile = "D:\work\mmRadar\DataCapture\data_07_14.setup.json";
% path_to_setupjsonfile = "C:\ti\mmwave_studio_03_01_04_04\mmWaveStudio\PostProc\data_17_06_1920.setup.json";
[firstFrameTime, allFrameTimes] = MyRawDataReader(path_to_setupjsonfile);
% RealTimeRangeAngle(path_to_setupjsonfile)

% 显示所有帧的时间戳
if ~isempty(allFrameTimes)
    nFrames = length(allFrameTimes);
    fprintf('\n===== 所有帧的时间戳（微秒） =====\n');
    fprintf('首帧绝对时间: %s\n', char(allFrameTimes(1)));
    for i = 1:nFrames
        timeOffset_us = milliseconds(allFrameTimes(i) - allFrameTimes(1)) * 1000;
        fprintf('  帧 %4d: %.0f us\n', i, timeOffset_us);
    end
end