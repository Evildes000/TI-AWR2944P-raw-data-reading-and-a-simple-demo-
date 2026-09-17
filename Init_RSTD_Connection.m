function ErrStatus = Init_RSTD_Connection(RSTD_DLL_Path)
    % 本文件用于和mmWaveStudio建立连接
    % 在运行脚本之前，在 mmWaveStudio Luashell 中键入 RSTD.NetStart ()，这将打开2777端口
    % 如果没有错误，将返回30000

    % WHICH ITEM displays the full path for ITEM.
    % strcmp  一致返回1，否则返回0
    % 判断是否已加载RtttNetClient
    if (strcmp(which('RtttNetClientAPI.RtttNetClient.IsConnected'),''))
        % 在打开MATLAB后首先运行本代码
        disp('Adding RSTD Assembly');
        % NET是Matlab提供的可以调用windows dll 文件的API。该函数返回一个NET.Assembly class
        RSTD_Assembly = NET.addAssembly(RSTD_DLL_Path);
        % 如果class names of the added assembly和预定的字符串不符，报错
        if ~strcmp(RSTD_Assembly.Classes{1},'RtttNetClientAPI.RtttClient')
            disp('RSTD Assembly not loaded correctly. Check DLL path');
            ErrStatus = -10;
            return
        end
        % 若class names of the added assembly和预定的字符串相符，设置连接状态为1
        Init_RSTD_Connection = 1;
    % 已加载但没有连接，则连接
    elseif ~RtttNetClientAPI.RtttNetClient.IsConnected() 
        Init_RSTD_Connection = 1;
    % 否则连接失败，返回0
    else
        Init_RSTD_Connection = 0;
    end
    

    % 若连接成功
    if Init_RSTD_Connection
        disp('Initializing RSTD client');
        % 初始化客户端。返回0则初始化成功
        ErrStatus = RtttNetClientAPI.RtttNetClient.Init();
        if (ErrStatus ~= 0)
            disp('Unable to initialize NetClient DLL');
            return;
        end
        disp('Connecting to RSTD client');
        % 建立与客户端的连接
        ErrStatus = RtttNetClientAPI.RtttNetClient.Connect('127.0.0.1',2777);
        if (ErrStatus ~= 0)
            disp('Unable to connect to mmWaveStudio');
            disp('Reopen port in mmWaveStudio. Type RSTD.NetClose() followed by RSTD.NetStart()');
            return;
        end
        pause(1);
    end
    disp('Sending test message to RSTD');
    % MATLAB 向 mmWaveStudio 发送了一条 Lua 脚本命令。mmWave中打印Running script from MATLAB\n
    Lua_String = 'WriteToLog("Running script from MATLAB\n", "green")';
    % 返回值为30000则说明命令发送成功
    ErrStatus = RtttNetClientAPI.RtttNetClient.SendCommand(Lua_String);
    if (ErrStatus ~= 30000)
        disp('mmWaveStudio Connection Failed');
    end
    disp('Test message success');
end
