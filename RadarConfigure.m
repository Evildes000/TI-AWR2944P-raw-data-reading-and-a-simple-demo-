function RadarConfigure
    %% 本文件用于 通过lua脚本，向mmwave studio发送雷达的配置参数  
	%% 打开studio并等待FTDI显示connected后即可运行该文件
    fprintf('\n----------RadarConfig-----------\n');
    addpath(genpath('.\'))
    % RtttNetClientAPI.dll 是一个允许外部程序控制mmWave的动态链接库。通过调用它其中包含的API可以实现
    % 向mmWave发送lua命令或配置参数，从而实现对雷达的自动化控制
    RSTD_DLL_Path = 'C:\ti\mmwave_studio_03_01_04_04\mmWaveStudio\Clients\RtttNetClientController\RtttNetClientAPI.dll';
    ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path); 
    if (ErrStatus ~= 30000)
        disp('Error inside Init_RSTD_Connection');
        return;
    end
    % lua脚本文件地址，雷达参数配置在该lua脚本
	% 注意: 先把 Scripts\DataCapture_AWR2944P.lua 复制到 mmWaveStudio\Scripts\ 目录下
	strFilename='C:\\ti\\mmwave_studio_03_01_04_04\\mmWaveStudio\\Scripts\\DataCapture_AWR2944P.lua'; 
    % sprintf 将字符串按照给定顺序拼接在一起。dofile是lua的标准函数，意为加载加载并运行这个文件
    Lua_String = sprintf('dofile("%s")',strFilename);
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);
end