

capture_time = 100000

--data_folder_path = "C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\"
-- data_folder_path = "D:\\DataTi\\"

data_folder_path = "D:\\work\\multi_model\\radar_data"
-- data_folder_path = "D:\\work\\mmRadar\\DataCapture"
data_file_name = "adc_data.bin"

adc_data_path   = data_folder_path  ..data_file_name
--adc_data_path   = "C:\\ti\\mmwave_studio_02_01_01_00\\mmWaveStudio\\PostProc\\test_data2.bin"
jsonFilePath_Capture = data_folder_path  .."AWR2944p.setup.json"
jsonFilePath_mmwave = data_folder_path .."AWR2944p.mmwave.json"

RSTD.Sleep(1000)
print("1")
RSTD.Sleep(1000)
print("2")
RSTD.Sleep(1000)
print("3")
RSTD.Sleep(1000)


RSTD.Sleep(1000)
print("Capturing!")



--Start Record ADC data
ar1.CaptureCardConfig_StartRecord(adc_data_path, 1)
RSTD.Sleep(1000)

--Trigger frame
ar1.StartFrame()
--RSTD.Sleep(capture_time)

--Post process the Capture RAW ADC data
--ar1.StartMatlabPostProc(adc_data_path)
--WriteToLog("Please wait for a few seconds for matlab post processing .....!!!! \n", "green")
--RSTD.Sleep(10000)

ar1.JsonExport(jsonFilePath_Capture,jsonFilePath_mmwave)


--ar1.StopFrame()
