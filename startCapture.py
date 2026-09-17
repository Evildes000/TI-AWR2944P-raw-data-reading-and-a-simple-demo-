#############################################
####  Author: Yadong Li, Ruixu Geng   #######
####  Date: 2023.04                   #######
#############################################

import recvUDPdata
from datetime import datetime
import threading
import time
import socket

currentTime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
successFlag = 0
collect_time = 20 # 300s
save_filename = 'test'


# pdb.set_trace()
# 创建一个线程，并在这个线程中执行目标函数，给目标函数传入所给的参数
azi_radar = threading.Thread(target = recvUDPdata.captureSingleRadarData, args = (currentTime, save_filename))

print("Start Radar")

# 开始采集雷达数据
azi_radar.start()

i = 0
while i < collect_time:
    i = i+1
    time.sleep(1)
    print(i)

print("Program Finished! Start Saving Data")
time.sleep(5)
print("Finish!")

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
localIP = "192.168.33.30"
localPort = 4096
clientSocket.bind((localIP, localPort))
clientSocket.sendto(b'\x5a\xa5\x06\x00\x00\x00\xaa\xee', ('192.168.33.180', 4096)) # 向目的地址发送停止采集的命令
clientSocket.close()
print("mmwave radar closed")
print(successFlag)



