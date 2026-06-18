% 这个程序只针对AWR2944P且：
% -- ADC的采样数据只有real类型（即直接对中频信号采样）
% -- ADC的采样位深为2（16bits），即每个采样值用16位比特表示
% 
% Syntax:
% =========
%     rawDataReader('JSON setup File name','raw data file name', 'radarCube data file name', 'debug plot')
%          - 'JSON setup File name', JSON setup file
%          - 这里的setup file 就是用来配置Connection tag里选项的文件
%          - 'raw data file name', file to save the raw ADC data
%          - 'radarCube data file name', file to save radar cube data  
%          - 'debug plot', flag to enable plot of raw data and radar cube
%
%
function MyRawDataReader(setupJsonFileName)


    global adcDataParams                    % contains ADC parameters
    global chParams                         % contains channel parameters
    global frameParams                      % contains frame parameters
    global fileParams                       % contains bin file parameters
    global dataSet                          % contains data from all bin files
  
    % global Params                           % contains parameters
    % global DataSet                          % contains all data from files
    % Read configuration and setup files
    setupJSON = jsondecode(fileread(setupJsonFileName));

    % Read mmwave device JSON file
    % setup file 里面包含了 mmWave device文件，该文件包含配置profile, chirp和frame的参数
    jsonMmwaveFileName = setupJSON.configUsed;
    mmwaveJSON = jsondecode(fileread(jsonMmwaveFileName));

    % Print parsed current system parameter
    fprintf('mmwave Device:%s\n', setupJSON.mmWaveDevice);

    % Read bin file name
    % Get bin file path
    binFilePath = setupJSON.capturedFiles.fileBasePath;
    % Count how many bin files are captured, at least one bin file 
    numBinFiles = length(setupJSON.capturedFiles.files);
    if( numBinFiles < 1)
        error('Bin File is not available');
    end  
    
    % add numBinFiles to aforementioned Params 
    fileParams.numBinFiles = numBinFiles;

    % 将每一个bin文件与其路径相对应
    for idx=1:numBinFiles
        fileParams.binFileName{idx} = strcat(binFilePath, '\', setupJSON.capturedFiles.files(idx).processedFileName);
    end

    % Generate ADC data parameters
    dp_generateParams(mmwaveJSON);

    % Generate radar cube parameters
    % radarCubeParams = dp_generateRadarCubeParams(mmwaveJSON);


    % Validate configuration 
    % 这里只验证LVDS的个数，是否交织
    % validConf = dp_validateDataCaptureConf(setupJSON, mmwaveJSON);
    % if(validConf == false)
    %   error("Configuraion from JSON file is not Valid");
    % end
     


    % 所有文件包含的总帧数
    % Params.NFrame = 0;
    % for idx = 1:numBinFiles
    %     % 打开文件成功则会返回一个非负整数，否则返回-1。
    %     % 打开成功时errmsg为空，否则errmsg中含有报错信息 
    % 
    %     % fid_rawData用来存储每个binfile对应的fid(类似于文件指针)
    %     [Params.fid_rawData(idx), errmsg] = fopen(binFileName{idx}, 'r');
    %     if(Params.fid_rawData(idx) == -1)
    %         fprintf("Can not open Bin file %s, - %s\n",binFileName{idx}, errmsg); 
    %         error('Quit with error');
    % 
    %     else
    %         DataSet = dp_loadDataPerFile(Params.binFileName{idx});
    %     end   
    % 
    % 
    % 
    %     % Calculate number of Frames in bin File 
    %     try
    %         Params.NFramePerFile(idx) = dp_getNumberOfFrameFromBinFile(binFileName{idx});
    %         Params.NFrame = Params.NFrame + Params.NFramePerFile(idx);
    %     catch
    %         if(Params.NFramePerFile(idx) == 0)
    %             error("Not enough data in binary file");
    %         end
    %     end
    % end


    dataSet.sampleRx = {};
    for idx = 1:numBinFiles
    % 打开文件成功则会返回一个非负整数，否则返回-1。
    %     打开成功时errmsg为空，否则errmsg中含有报错信息 
    % 
    %     fid_rawData用来存储每个binfile对应的fid(类似于文件指针)
        [fileParams.fid_rawData(idx), errmsg] = fopen(fileParams.binFileName{idx}, 'r');
        if fileParams.fid_rawData(idx) == -1
            fprintf("can't open bin file %d \n %s", fileParams.binFileName{idx}, errmsg)
        end

        rawData = fread(fileParams.fid_rawData(idx), 'uint16');
        % dataSet.rawData{idx} = rawData;
        if (adcDataParams.chanInterleave == 1) && (adcDataParams.dataFmt == 0)
            % non-interleaved and real
            
            % calculate all bytes number of a file 
            totalSamples = length(rawData);
            % calculate how many samples for each Rx
            numSamplesPerRx= totalSamples / chParams.numRxChan;

            for iRx = 1:chParams.numRxChan
               dataSet.sampleRx{iRx} = rawData(1+numSamplesPerRx*(iRx - 1):numSamplesPerRx+numSamplesPerRx*(iRx - 1));
            end
            dp_generateDataCube()
        end
    
    end

    
    % Export data
    % dp_exportData(rawDataFileName, radarCubeDataFileName);
    
    %close and delete handles before exiting
    % for idx = 1: numBinFiles
    %    fclose(Params.fid_rawData(idx)); 
    % end
    % close all;
end



%  -----------------------------------------------------------------------
%  Description:    This function generates ADC Parameters, channel
%                  parameters, frame parameters and rf parameters
%  Input:          mmwaveJSON
%  -----------------------------------------------------------------------
function dp_generateParams(mmwaveJSON)

    C = 3 * 10e8;
    global adcDataParams
    global chParams
    global frameParams
    global rfParams

    frameCfg = mmwaveJSON.mmWaveDevices.rfConfig.rlFrameCfg_t;
    
    % 2944p只支持模式0，即所有数据为real形式
    adcDataParams.dataFmt = mmwaveJSON.mmWaveDevices.rfConfig.rlAdcOutCfg_t.fmt.b2AdcOutFmt;
    
    % 用来指示I路和Q路的数据哪一个在高位，哪一个在低位。IQ数据各占16位。由于2944p只支持real格式的数据
    % 所以这个参数并不重要。
    adcDataParams.iqSwap = mmwaveJSON.mmWaveDevices.rawDataCaptureConfig.rlDevDataFmtCfg_t.iqSwapSel;
    
    % 0--交织，1--非交织
    % TDM--只支持1， DDM--只支持0
    adcDataParams.chanInterleave = mmwaveJSON.mmWaveDevices.rawDataCaptureConfig.rlDevDataFmtCfg_t.chInterleave;
    
    % adcDataParams.numChirpsPerFrame = frameCfg.numLoops  * (frameCfg.chirpEndIdx - frameCfg.chirpStartIdx + 1);
    % 位深，即每个采样数据用多少位数来表示。2944P只支持16位的位深
    adcDataParams.adcBits = mmwaveJSON.mmWaveDevices.rfConfig.rlAdcOutCfg_t.fmt.b2AdcBits;
    
    
    rxChanMask = sscanf(mmwaveJSON.mmWaveDevices.rfConfig.rlChanCfg_t.rxChannelEn, '0x%x');
    % 将16进制的mask转化为10进制表示
    chParams.numRxChan = dp_numberOfEnabledChan(rxChanMask);
    txChanMask = sscanf(mmwaveJSON.mmWaveDevices.rfConfig.rlChanCfg_t.txChannelEn, '0x%x');
    chParams.numTxChan = dp_numberOfEnabledChan(txChanMask);

    % there is another parameter called laneEn right above this parameter,
    % but it doesn't stand for number of LVDS lanes in use.
    % chParams.numLVDS = mmwaveJSON.mmWaveDevices.rawDataCaptureConfig.rlDevLvdsLaneCfg_t.laneParamCfg;
    
    % 读取lvds的mask并将其转化位十进制表示
    lvdsMask = sscanf(mmwaveJSON.mmWaveDevices.rawDataCaptureConfig.rlDevLvdsLaneCfg_t.laneParamCfg, '0x%x');
    chParams.numLvds = dp_numberOfEnabledChan(lvdsMask);


    frameParams.numAdcSamplesPerChirps = mmwaveJSON.mmWaveDevices.rfConfig.rlProfiles.rlProfileCfg_t.numAdcSamples;
    
    % frame中chirp的总数
    frameParams.numChirpsPerFrame = frameCfg.numLoops  * (frameCfg.chirpEndIdx - frameCfg.chirpStartIdx + 1);
    frameParams.framePeriority = mmwaveJSON.mmWaveDevices.rfConfig.rlFrameCfg_t.framePeriodicity_msec;
    
    % 一个frame中的unique chirp pattern重复多少次
    % 比如chirp_0,chirp_1, chirp_2 重复发送100次
    frameParams.numDopplerChirps = mmwaveJSON.mmWaveDevices.rfConfig.rlFrameCfg_t.numLoops;


    % ------------------calculate rf paramters---------------------
    profileCfg = mmwaveJSON.mmWaveDevices.rfConfig.rlProfiles.rlProfileCfg_t;
    rfParams.startFreq = profileCfg.startFreqConst_GHz;
    % Slope const (MHz/usec)
    rfParams.freqSlope = profileCfg.freqSlopeConst_MHz_usec; 
    % ADC sampling rate in Msps
    rfParams.sampleRate = profileCfg.digOutSampleRate / 1e3; 
    % Generate radarCube parameters

    rfParams.numRangeBins = pow2(nextpow2(frameParams.numAdcSamplesPerChirps)); 
    % rfParams.numDopplerBins = radarCubeParams.numDopplerChirps;
    % rfParams.bandwidth = abs(rfParams.freqSlope * profileCfg.numAdcSamples / profileCfg.digOutSampleRate);
    rfParams.adcBandwidth = abs(rfParams.freqSlope * frameParams.numAdcSamplesPerChirps / profileCfg.digOutSampleRate);
    rfParams.sweepBandwidth = profileCfg.rampEndTime_usec * rfParams.freqSlope;
    % rfParams.rangeResolutionsInMeters = C * rfParams.sampleRate / (2 * rfParams.freqSlope * rfParams.numRangeBins * 1e6);
    fprintf("C is:%d\n", C)
    fprintf("sweep bandwidth is:%d\n", rfParams.sweepBandwidth)
    rfParams.rangeResolutionsInMeters = C / (2*rfParams.sweepBandwidth * 10e6);
    rfParams.dopplerResolutionMps =  C  / (2*rfParams.startFreq * 1e9 *...
                                        (profileCfg.idleTimeConst_usec + profileCfg.rampEndTime_usec  ) *...
                                        1e-6 * frameParams.numDopplerChirps * chParams.numTxChan);

    % 判断adc参数是否合法
    % dp_printADCDataParams(adcDataParams);
    % Calculate size of one ADC sample in bytes
    if(adcDataParams.adcBits == 2) % 2: 16bits
        if (adcDataParams.dataFmt == 0) % 0: real
            % real data, one sample is 16bits=2bytes
            gAdcOneSampleSize = 2; 
        else
            fprintf('Error: unsupported ADC dataFmt.Please select Format 0');
        end
    else
        fprintf('Error: unsupported ADC bits (%d). Please select adcBit: 2', adcDataParams.adcBits);
    end    
    
    % 包括所有接收天线(In Bytes)
    % dataSizeOneChirp = gAdcOneSampleSize * frameParams.numAdcSamplesPerChirps * chParams.numRxChan;
    % 一个frame包含所有接收天线的chirps
    % Params.dataSizeOneFrame = dataSizeOneChirp * adcDataParams.numChirpsPerFrame;
    % Params.dataSizeOneChirp = dataSizeOneChirp;
    % Params.adcDataParams = adcDataParams;
    
    dp_printParams();
end


%  -----------------------------------------------------------------------
%  Description:    This function prints ADC raw data Parameters
%  Input:          adcDataParams
%  Output:         None
%  -----------------------------------------------------------------------
function dp_printParams()
    global adcDataParams;
    fprintf('------------------------------------------\n');
    fprintf('Input ADC data parameters:\n');
    fprintf('    dataFmt:%d (0: real; 1 or 2: complex)\n ',adcDataParams.dataFmt);
    fprintf('    iqSwap:%d (0: not swapped, I first; 1: swapped, Q first)\n',adcDataParams.iqSwap);
    fprintf('    chanInterleave:%d (0: interleaved; 1: non-interleaved)\n',adcDataParams.chanInterleave);    
    % fprintf('    numChirpsPerFrame:%d\n',adcDataParams.numChirpsPerFrame);
    % fprintf('    dataSizeOneFrame: %d\n', Params.dataSizeOneFrame);
    % fprintf('    numOfFrame: %d\n', Params.NFrame);
    fprintf('    adcBits:%d (2: 16 bits; 1: 14 bits; 0: 12 bits)\n',adcDataParams.adcBits);
    % fprintf('    numRxChan:%d\n',adcDataParams.numRxChan);   
    % fprintf('    numAdcSamples:%d\n',adcDataParams.numAdcSamplesPerChirps);   
    % fprintf('    dataSizeOneChirp: %d\n', Params.dataSizeOneChirp);
    % fprintf('    dataSizeOneFrame: %d\n', Params.dataSizeOneFrame);


    global chParams
    fprintf('------------------------------------------\n');
    fprintf('Input ADC data parameters:\n');
    fprintf('    numRxChann:%d\n',chParams.numRxChan);   
    fprintf('    numTxChann:%d\n',chParams.numTxChan);  
    fprintf('    numLvds:%d\n',chParams.numLvds);  


    global frameParams
    fprintf('------------------------------------------\n');
    fprintf('frame parameters:\n');
    fprintf('    numAdcSamplesPerChirps:%d\n',frameParams.numAdcSamplesPerChirps);   
    fprintf('    numChirpsPerFrame:%d\n',frameParams.numChirpsPerFrame);   
    fprintf('    framePeriority:%d\n',frameParams.framePeriority);   
    
    
    global rfParams
    fprintf('------------------------------------------\n');
    fprintf('rf parameters:\n');
    fprintf('    startFreq:%d\n', rfParams.startFreq);   
    fprintf('    freqSlope:%d(MHz/us)\n', rfParams.freqSlope);
    fprintf('    sampleRate:%d(ksps)\n', rfParams.sampleRate);

    fprintf('    numRangeBins:%d\n', rfParams.numRangeBins);   
    fprintf('    adc bandwidth:%d(GHz)\n', rfParams.adcBandwidth);
    fprintf('    sweep bandwidth:%d(MHz)\n', rfParams.sweepBandwidth);
    fprintf('    rangeResolutionsInMeters:%d\n', rfParams.rangeResolutionsInMeters);
    fprintf('    dopplerResolutionMps:%d\n', rfParams.dopplerResolutionMps);   
    
end



%  -----------------------------------------------------------------------
%  Description:    This function counts number of enabled channels from 
%                  channel Mask.
%  Input:          chanMask
%  Output:         Number of channels
%  -----------------------------------------------------------------------
function [count] = dp_numberOfEnabledChan(chanMask)
    
    MAX_RXCHAN = 4;
    count = 0;
    for chan= 0:MAX_RXCHAN - 1
        bitVal = pow2(chan);
        if (bitand(chanMask,bitVal) == (bitVal))
            count = count + 1;
            chanMask = chanMask-bitVal;
            if(chanMask == 0) 
                break;
            end
        end
    end
end



%  -----------------------------------------------------------------------
%  Description:    生成4维矩阵[num_RxAntenna ,num_chirpsPerFrame, num_adcSamplesPerChirps, num_frame] 
%  Input:          index of Rx
%  -----------------------------------------------------------------------
function dp_generateDataCube()
    global dataSet
    global frameParams
    global chParams
    
    dataSet.cubeData = {};
    % generate data cube for each Rx
    for irx = 1:chParams.numRxChan
        % 每个天线总共接受了多少个samples
        frameParams.numFrame = length(dataSet.sampleRx{irx}) / (frameParams.numAdcSamplesPerChirps * frameParams.numChirpsPerFrame); 
        % 将所给数据排列成所给的格式
        dataSet.cubeData{irx} = reshape(dataSet.sampleRx{irx},[frameParams.numChirpsPerFrame, frameParams.numAdcSamplesPerChirps, frameParams.numFrame]);
    end
    

    % combine Rx's data cube into a 4-dim cube
    if (chParams.numRxChan == 4)
        dataSet.finalCube = cat(4, dataSet.cubeData{1}, dataSet.cubeData{2}, dataSet.cubeData{3}, dataSet.cubeData{4});
    elseif (chParams.numRxChan == 2)
        dataSet.finalCube = cat(4, dataSet.cubeData{1}, dataSet.cubeData{2});
    else
        fprintf("number of Rx Channel %d is not support\n",chParams.numRxChann)
    end

    fprintf("size of data cube is:[%d, %d, %d, %d]\n", size(dataSet.finalCube))
    
end


