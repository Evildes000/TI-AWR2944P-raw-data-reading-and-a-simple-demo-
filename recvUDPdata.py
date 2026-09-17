#############################################
####  Author: Yadong Li, Ruixu Geng   #######
####  Date: 2023.04                   #######
#############################################



import os
import socket
import sys
import re
import _thread
import time


frames_idx = []

def process_data(currentTime, save_filename='test'):
    global save_frame_num
    global successFlag

    ipadress = ("192.168.33.30", int(4098)) # 4098端口用来接收ADC数据
    # RECVBUFFSIZE = 50 * 1000 * 1000 * 40
    RECVBUFFSIZE = 1000*1000
    # udp_socket负责从DCA1000接收数据，保持开启状态
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(ipadress)

    # 将内核缓冲区增加到recvbuffsize的需要大小
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, RECVBUFFSIZE)
    wait_time = 5
    udp_socket.settimeout(wait_time)

    print('Server端已准备就绪！等待数据传输')

    # clientSocket负责向毫米波雷达发送控制指令。指令发送结束后就将该 socket关闭。
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    localIP = "192.168.33.30"
    localPort = 4096
    clientSocket.bind((localIP, localPort))
    # x05:启动；x06:停止
    clientSocket.sendto(b"\x5a\xa5\x05\x00\x00\x00\xaa\xee", ('192.168.33.180', 4096))  # 向雷达发送启动命令
    clientSocket.close()
    time.sleep(0.5)
    print("Azi mmwave radar start")

    
    save_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar_data", currentTime, save_filename)
    print(f"save folder is: {save_folder}")
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)
    timestamp_file = os.path.join(save_folder,"timestamp.txt")
    if os.path.exists(timestamp_file):
        os.remove(timestamp_file)
    
    udp_filename = os.path.join(save_folder,"udpData.dat")
    print(f"path of udp data: {udp_filename}")
    f = open(timestamp_file,'a')

    f_udp = open(udp_filename, "wb")
    p_header = b'\x03\x02\x08\x00'  #作者自己规定的分割符，用来分隔每次写入到文件中的雷达数据
    first_packet_flag = 1

    while True:
        try:
            # 从套接字接收数据，缓冲区为2048字节
            currUdpPacketData, ipaddr = udp_socket.recvfrom(2048)
            
            # data_format: [Sequence_number(4 bytes)][Bytes Count(6 bytes)][Raw mode data(48-1462bytes)]
            curr_seq_num = int.from_bytes(currUdpPacketData[0:3], byteorder='little')

            if(first_packet_flag == 1):
                prev_seq_num = curr_seq_num-1
                first_packet_flag = 0
                dataStreamStarTime = time.time()
                f.write("Azi start time:" + str(dataStreamStarTime))
                f.write('\n')
                f.flush()
                print(dataStreamStarTime)
                print('RECVING !')
                # 杀死占用端口4096的线程，避免下次使用4096端口时失败
                _thread.start_new_thread(close_mmwave_control, ("Thread-2",))
        
            if (curr_seq_num - prev_seq_num) != 1:
                print('PacketLost!  id:' + str(curr_seq_num))

            prev_seq_num = curr_seq_num
            packet_len = len(currUdpPacketData)
            # 将数据包的长度转化为小端序（低字节）
            # packet_len.to_bytes(2, byteorder='little')
            
            f_udp.write(p_header + packet_len.to_bytes(2, byteorder='little') + currUdpPacketData)
            f_udp.flush()

        except:
            print('Azi RECV ENDED!')
            timeEnd = time.time() - wait_time
            print(timeEnd)

            try:
                time_difference = timeEnd - dataStreamStarTime
            except:
                print("有雷达未能成功启动，程序中断")
                sys.exit(1)
            if time_difference < 0.1:
                print("有雷达未能成功启动，程序中断")
                sys.exit(1)
            f.write("Azi end time: " + str(timeEnd))
            f.write('\n')
            f.flush()

            f.close()
            f_udp.close()
            break



def close_mmwave_control(threadName):
    try:
        x = os.popen("netstat -ano | findstr 4096").read()
        xx = re.findall(r'\d+', x)
        print(x)
        cmdstr = "taskkill -PID " + str(xx[5]) + " -F"
        x = os.popen(cmdstr).read()
        print(x)
        print("mmWavestudio spy control closed successfully!")
    except:
        print("no mmWavestudio spy control")



def write_UDP_data(f_udp, p_header, packet_len, currUdpPacketData):
    f_udp.write(p_header + packet_len.to_bytes(2, byteorder='little') + currUdpPacketData)



def captureSingleRadarData(currentTime, save_filename):
    global successFlag
    # pdb.set_trace()

    global save_frame_num
    global timestamps
    timestamps = []
    save_frame_num = 0

    process_data(currentTime, save_filename)
    print(f"number of saved frames: {save_frame_num}")
    print("Radar Finished")

