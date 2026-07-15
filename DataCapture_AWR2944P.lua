-- ============================================================
-- DataCapture.lua  ——  AWR2944P + DCA1000 雷达配置脚本
-- 适配: mmWave Studio 03.01.04.04
-- 用法: 在 MATLAB 中运行 RadarConfigure.m，它会自动调用此脚本
--      或在 mmWave Studio 的 LuaShell 中手动执行: dofile("DataCapture.lua")
-- ============================================================

-- ==================== 1. 复位与连接 ====================
ar1.FullReset()
ar1.SOPControl(2)

-- COM 口: 根据设备管理器中 "XDS110 Class Application/User UART" 的端口号修改
-- 波特率: 115200 (固定)
-- 超时: 1000ms
ar1.Connect(9, 115200, 1000)   -- 请确认 COM 口号，你的 setup.json 中是 COM9
RSTD.Sleep(5000)
WriteToLog("\n========== AWR2944P Radar Configuration Start ==========\n", "green")

-- ==================== 2. 下载固件 ====================
-- AWR2944P 使用的 BSS (Radar Subsystem) 和 MSS (Master Subsystem) 固件路径
BSS_FW = "C:\\ti\\mmwave_studio_03_01_04_04\\rf_eval_firmware\\radarss\\xwr2x4xp_radarss_rprc.bin"
MSS_FW = "C:\\ti\\mmwave_studio_03_01_04_04\\rf_eval_firmware\\masterss\\awr2xxx_mmwave_full_mss_rprc.bin"


-- 下载 BSS 固件
if (ar1.DownloadBSSFw(BSS_FW) == 0) then
    WriteToLog("BSS FW Download Success\n", "green")
else
    WriteToLog("BSS FW Download Failure\n", "red")
    return
end

-- 下载 MSS 固件
if (ar1.DownloadMSSFw(MSS_FW) == 0) then
    WriteToLog("MSS FW Download Success\n", "green")
else
    WriteToLog("MSS FW Download Failure\n", "red")
    return
end


-- SPI 上电
if (ar1.PowerOn(0, 1000, 0, 0) == 0) then
    WriteToLog("Power On Success\n", "green")
else
    WriteToLog("Power On Failure\n", "red")
    return
end


-- RF 上电
if (ar1.RfEnable() == 0) then
    WriteToLog("RF Enable Success\n", "green")
else
    WriteToLog("RF Enable Failure\n", "red")
    return
end


-- ==================== 3. 通道与 ADC 配置 ====================
-- ChanNAdcConfig 物理层面使能天线
-- 参数: Rx0~Rx3(1=使能,0=禁用), Tx0~Tx3(1=使能), ADC位数, 输出格式, IQSwap
-- ADC位数: 2=16bit。 2944p只支持16bit
-- 输出格式: 1=实部, 2=复(I/Q)。2944P只支持输出实数
-- IQSwap: 0=不交换(I,Q), 1=交换(Q,I)。对2944P无影响
-- 你的配置: Rx0~3全开(1,1,1,1), Tx0和Tx1开启(1,1,0,0), 16bit ADC, 实数输出
if (ar1.ChanNAdcConfig(1, 1, 1, 1,   1, 1, 0, 0,   2, 0, 0) == 0) then
-- if (ar1.ChanNAdcConfig(1, 0, 1, 1, 1, 1, 1, 2, 1, 0) == 0) then   
    WriteToLog("ChanNAdcConfig Success\n", "green")
else
    WriteToLog("ChanNAdcConfig Failure\n", "red")
end


-- ==================== 4. 射频相关配置 ====================

-- 低功耗模式：关闭 LDO bypass + 低功耗 ADC
if (ar1.LPModConfig(0, 1) == 0) then
    WriteToLog("LPModConfig Success\n", "green")
else
    WriteToLog("LPModConfig Failure\n", "red")
end

-- RF LDO Bypass
if (ar1.RfLdoBypassConfig(0x3) == 0) then
    WriteToLog("RfLdoBypass Success\n", "green")
else
    WriteToLog("RfLdoBypass Failure\n", "red")
end

-- RF 初始化
if (ar1.RfInit() == 0) then
    WriteToLog("RfInit Success\n", "green")
else
    WriteToLog("RfInit Failure\n", "red")
end

RSTD.Sleep(1000)


-- ==================== 5. 数据路径配置 (LVDS) ====================
-- DataPathConfig: 接口选择, 数据格式pkt0, 数据格式pkt1
--   intfSel=1 → LVDS; transferFmtPkt0=1 → 标准ADCu数据
if (ar1.DataPathConfig(1, 1, 0) == 0) then
    WriteToLog("DataPathConfig Success\n", "green")
else
    WriteToLog("DataPathConfig Failure\n", "red")
end

-- LVDS 时钟配置: laneClk, dataRate
if (ar1.LvdsClkConfig(1, 1) == 0) then
    WriteToLog("LvdsClkConfig Success\n", "green")
else
    WriteToLog("LvdsClkConfig Failure\n", "red")
end

-- LVDS Lane 配置
-- laneFrmtCfg=2 (16-bit), lane1=1 Rx1使能, lane2=0, lane3=0, lane4=0
-- msbFst=1, pktEndPls=0, crcEn=0
-- (0, 1, 1, 0, 0, 1, 0, 0)
-- if (ar1.LVDSLaneConfig(2, 1, 0, 0, 0, 1, 0, 0) == 0) then
if (ar1.LVDSLaneConfig(0, 1, 1, 0, 0, 1, 0, 0) == 0) then
    WriteToLog("LVDSLaneConfig Success\n", "green")
else
    WriteToLog("LVDSLaneConfig Failure\n", "red")
end


WriteToLog("====== A ======\n","green")

WriteToLog("====== B ======\n","green")

-- ==================== 6. Profile 配置 (Chirp 波形) ====================
-- ProfileConfig(profileId,   startFreq_GHz, idleTime_us,
--                adcStartTime_us, rampEndTime_us, txPowerBackoff_dB,
--                txPhaseShifter_deg, freqSlope_MHz_us, txStartTime_us,
--                numAdcSamples, digOutSampleRate_ksps,
--                hpfCornerFreq1, hpfCornerFreq2, rxGain_dB)
--
-- ===== 5 GHz 带宽配置 =====
-- Bandwidth = freqSlope × (rampEndTime - adcStartTime)
--           = 50 × (106 - 6) = 5000 MHz = 5.0 GHz
--   起始频率: 77 GHz
--   Idle Time: 150 us  (chirp变长，留足空闲)
--   ADC 开始时间: 6 us
--   Ramp 结束时间: 106 us
--   频率斜率: 50 MHz/us
--   采样点数: 512  (有效采样窗 = 512/10000 = 51.2us，覆盖更多ramp)
--   采样率: 10000 ksps (10 MHz)
--   接收增益: 0x1E (30 dB)
if (ar1.ProfileConfig(0, 77.000000024, 150.01, 6, 100.03, 0, 0, 0, 0, 0, 0, 0, 0, 35.92, 0, 512, 10000, 2216755200, 131072, 30, 0, 0, 0) == 0) then
    WriteToLog("ProfileConfig Success\n", "green")
else
    WriteToLog("ProfileConfig Failure\n", "red")
end

WriteToLog("====== C ======\n","green")
-- ==================== 7. Chirp 配置 (天线映射) ====================
-- ChirpConfig(startIdx, endIdx, profileId,
--            startFreqVar, freqSlopeVar, idleTimeVar, adcStartTimeVar,
--            Tx0En, Tx1En, Tx2En, Tx3En)
--
-- TDM 模式:  chirp 轮流用 Tx0 和 Tx1 发送
if (ar1.ChirpConfig(0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0) == 0) then
    WriteToLog("ChirpConfig 0 (Tx0) Success\n", "green")
else
    WriteToLog("ChirpConfig 0 (Tx0) Failure\n", "red")
end



-- ==================== 8. Frame 配置 ====================
-- FrameConfig(chirpStartIdx, chirpEndIdx, numFrames, numLoops,
--             framePeriodicity_ms, triggerDelay, triggerSelect)
--
-- 你的 JSON 配置:
--   chirpStartIdx=0, chirpEndIdx=0, numLoops=128, numFrames=500
--   framePeriodicity=40ms, triggerSelect=1 (硬件触发)
--   这里 triggerSelect 改为 0 使用软件触发(更适合通过 MATLAB 控制)
if (ar1.FrameConfig(0, 0,   500, 128,   100, 0, 0) == 0) then
    WriteToLog("FrameConfig Success\n", "green")
else
    WriteToLog("FrameConfig Failure\n", "red")
end


-- ==================== 9. DCA1000 采集卡配置 ====================

-- 选择 DCA1000 采集设备
if (ar1.SelectCaptureDevice("DCA1000") == 0) then
    WriteToLog("SelectCaptureDevice DCA1000 Success\n", "green")
else
    WriteToLog("SelectCaptureDevice DCA1000 Failure\n", "red")
end

-- 以太网初始化 (DCA1000 的默认 IP 配置)
if (ar1.CaptureCardConfig_EthInit("192.168.33.30", "192.168.33.180",
                                  "12:34:56:78:90:12", 4096, 4098) == 0) then
    WriteToLog("CaptureCardConfig_EthInit Success\n", "green")
else
    WriteToLog("CaptureCardConfig_EthInit Failure\n", "red")
end

-- DCA1000 工作模式
--   eLogMode=1: 原始数据模式
--   eLvdsMode=2: AWR2944P(AR29xx→2)
--   eDataXferMode=1: LVDS 传输
--   eDataCaptureMode=2: 以太网流模式
--   eDataFormatMode=2: 14-bit
--   u8Timer=30s: 超时阈值
if (ar1.CaptureCardConfig_Mode(1, 2, 1, 2, 3, 30) == 0) then
    WriteToLog("CaptureCardConfig_Mode Success\n", "green")
else
    WriteToLog("CaptureCardConfig_Mode Failure\n", "red")
end

-- UDP 包间延迟 (微秒)
if (ar1.CaptureCardConfig_PacketDelay(25) == 0) then
    WriteToLog("CaptureCardConfig_PacketDelay Success\n", "green")
else
    WriteToLog("CaptureCardConfig_PacketDelay Failure\n", "red")
end


-- 设置DCA1000采集到的数据的保存路径
if (ar1.CaptureCardConfig_StartRecord("C:\\ti\\mmwave_studio_03_01_04_04\\mmWaveStudio\\PostProc\\adc_data.bin", 1) == 0 ) then
    WriteToLog("DCA1000 ARM Success\n", "green")
else
    WriteToLog("DCA1000 ARM Failure\n", "red")
end

-- ==================== 10. 开始采集 (由 MATLAB 上层的 SendCaptureCMD 控制) ====================
-- 注意: 此脚本执行到这就完成了所有配置。
-- 实际的 StartRecord / StartFrame 由 SendCaptureCMD.m 生成 FrameStart.lua 来控制。
-- 如果你希望直接在这里触发采集，取消下面几行注释:

-- adc_data_path = "D:\\work\\mmRadar\\DataCapture\\adc_data_test.bin"
-- ar1.CaptureCardConfig_StartRecord(adc_data_path, 1)
-- RSTD.Sleep(1000)
-- ar1.StartFrame()

WriteToLog("\n========== AWR2944P Configuration Complete ==========\n", "green")
WriteToLog("Ready for capture. Run SendCaptureCMD in MATLAB to start.\n", "green")
