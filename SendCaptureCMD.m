function [firstFrameTimestamp] = SendCaptureCMD
    %% 本文件用于 MATLAB发送指令给mmwave studio，控制DCA采集并回传数据
    %  输出:
    %    firstFrameTimestamp - datetime 对象，表示第一个数据帧的时间戳（壁钟时间）

    %% 保存文件路径设置
    % data_path为bin文件的保存文件夹，bin_name为设置的bin文件名(不含.bin，如\\adc_data_1)

    % data_path = 'D:\\MyDataset\\DatasetFile\\Action';
    data_path = 'D:\\work\\mmRadar\\DataCapture';
    
    bin_name = '\\adc_data_qc'; % 实际文件会产生Raw_0的后缀
    
    % 检查文件夹是否存在，如果不存在则创建
    if ~isfolder(data_path)
        mkdir(data_path);
    end    
    
    %% 修改采集数据的脚本文件
    % 设计bin文件目录
    str1 = strcat('adc_data_path="',data_path, bin_name,'.bin"'); 
    
    % 在 Lua 脚本中加入时间戳记录：StartFrame 时打印精确时间
    str = [str1, ...
           "ar1.CaptureCardConfig_StartRecord(adc_data_path, 1)", ...
           "RSTD.Sleep(1000)", ...
           "WriteToLog('__TIMESTAMP_START_FRAME__' .. os.date('%Y-%m-%d %H:%M:%S'), 'green')", ...
           "ar1.StartFrame()"];
    fid = fopen('C:\\ti\\mmwave_studio_03_01_04_04\\mmWaveStudio\\Scripts\\FrameStart.lua','w');
    for i = 1:length(str)
        fprintf(fid,'%s\n',str(i));
    end
    fclose(fid); % 关闭文件
    
    %% 配置雷达数据采集
    addpath(genpath('.\'))
    % Initialize mmWaveStudio .NET connection
    RSTD_DLL_Path = 'C:\\ti\\mmwave_studio_03_01_04_04\\mmWaveStudio\\Clients\\RtttNetClientController\\RtttNetClientAPI.dll';
    ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path);
    if (ErrStatus ~= 30000)
        disp('Error inside Init_RSTD_Connection');
        firstFrameTimestamp = NaT;
        return;
    end
    strFilename = 'C:\\ti\\mmwave_studio_03_01_04_04\\mmWaveStudio\\Scripts\\FrameStart.lua';
    Lua_String = sprintf('dofile("%s")',strFilename);
    
    % 记录发送命令前的时间（精确到毫秒）
    t_before = datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss.SSS');
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);
    
    t_after = datetime('now', 'Format', 'yyyy-MM-dd HH:mm:ss.SSS');
    % t_after 是真正采集首个帧的时间戳 
    
    % 计算首帧时间戳:
    % Lua 脚本流程: StartRecord → Sleep(1000ms) → WriteToLog → StartFrame
    % SendCommand 是同步的，dofile 返回时 StartFrame 刚好执行完毕
    % 因此 t_after 最接近首帧实际触发时间（误差约 10-20ms）
    firstFrameTimestamp = t_after;

    pyrunfile("D:\\work\\wireless_sensing\\camera_capture.py");
    
    %% 保存时间戳到文件（与bin文件同目录）
    new_data_path = regexprep(data_path, '\\\\', '\');
    new_bin_name = regexprep(bin_name, '\\\\', '\');
    bin_full_path = [new_data_path, new_bin_name, '_Raw_0.bin'];
    
    % 将时间戳写入 .timestamp.txt 文件
    timestamp_file = [new_data_path, new_bin_name, '_timestamp.txt'];
    fid_ts = fopen(timestamp_file, 'w');
    fprintf(fid_ts, 'first_frame_timestamp: %s\n', ...
            datestr(firstFrameTimestamp, 'yyyy-mm-dd HH:MM:SS.FFF'));
    fprintf(fid_ts, 't_before: %s\n', datestr(t_before, 'yyyy-mm-dd HH:MM:SS.FFF'));
    fprintf(fid_ts, 't_after:  %s\n', datestr(t_after, 'yyyy-mm-dd HH:MM:SS.FFF'));
    fprintf(fid_ts, 'bin_file: %s\n', bin_full_path);
    fclose(fid_ts);
    
    %% 打印bin文件保存路径
    fprintf('----\n开始采集雷达数据！\n');
    fprintf('首帧时间戳: %s\n', char(firstFrameTimestamp));
    fprintf('bin文件保存路径:\n');
    disp(['"', bin_full_path, '"']);
    fprintf('时间戳文件: "%s"\n', timestamp_file);
    fprintf('---------------------------\n\n');
end


