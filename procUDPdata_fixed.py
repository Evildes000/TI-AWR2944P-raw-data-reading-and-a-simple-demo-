#############################################
####  Author: Yadong Li, Dong Zhang   #######
####  Date: 2021.07                   #######
####  Fixed: 2026.07                  #######
####  AWR2944P non-interleave, real-only ADC
#############################################

import numpy as np
import os
import json


def fetchNewFramesData(obj):
    """
    Disp:
        fetch a frame from obj['frameDataBuffer']
    """

    newFramesData = np.array([])
    newFrameIndex = np.array([])
    flag = 0

    # frameDataBuff_index： 当前缓冲区已写入的字节数
    # oneFrameDataSize：一个frame所占的字节数
    # 计算当前缓冲区中有多少frame（向下取整）
    new_updated_frame_num = int(np.fix(obj['frameDataBuff_index'] / obj['oneFrameDataSize']));

    # frame数量大于1时有大量丢包
    if new_updated_frame_num > 1:
        print('Udp Lose')

    # frame数量大于0小于等于1时，处理新的frame
    if new_updated_frame_num > 0:
        flag = 1
        for i in range(0, new_updated_frame_num, 1):
            obj['frameId'] = obj['frameId'] + 1
            # 读取一个frame的数据
            currFrameData = obj['frameDataBuff'][0:obj['oneFrameDataSize']]
            # 缓冲区里存储的是int8类型，现在将缓冲区里的数据每两个一起读取（因为一个ADC Sample 是 16bit）
            currFrameData = np.frombuffer(currFrameData.data, dtype=np.int16,
                                          count=int(currFrameData.size / 2),
                                          offset=0)

            # 从原来的数据里删除已提取出的一帧的数据，为了维持总长度不变，进行0填充
            obj['frameDataBuff'] = np.concatenate(
                (obj['frameDataBuff'][obj['oneFrameDataSize']:], obj['zeroPadding']))
            # 计算frameDataBuff_index里剩余的字节数
            obj['frameDataBuff_index'] = obj['frameDataBuff_index'] - obj['oneFrameDataSize']
            if i == 0:
                newFramesData = np.array([currFrameData])
            else:
                newFramesData = np.concatenate((newFramesData, currFrameData[None, :]))
            newFrameIndex = np.concatenate((newFrameIndex, np.array([obj['frameId']])))

    return flag, newFramesData, newFrameIndex


def readOneUdpPacket(obj, currUdpData, first_packet=False):
    """
    Args
        obj: dict which contains frame id, size of a frame, and array to store all udp data for a frame
        currUdpData: one current udp data
    Disp:
        read currUdpData into obj['frameDataBuff']
    """

    # Udp中每个包的sequence number 占4个字节
    seqRatio = np.array([1, 256, 256 << 8, 256 << 16])
    # Udp中每个包的 bytes size 占6个字节
    dataSizeRatio = np.array([1, 256, 256 << 8, 256 << 16, 256 << 24, 256 << 32])
    flag = 0
    if currUdpData.size == 0:
        return flag

    currSeqNumArray = currUdpData[0:4]
    obj['currSeqNum'] = np.matmul(currSeqNumArray, seqRatio)
    dataSizeNumArray = currUdpData[4:10]
    obj['dataSizeTransed'] = np.matmul(dataSizeNumArray, dataSizeRatio)

    if obj['total_data_size'] != 0 and obj['dataSizeTransed'] == 0:
        return

    currUdpRawData = currUdpData[10:]
    udp_packet_size = currUdpData.size
    raw_data_size = udp_packet_size - 10

    obj['total_data_size'] = obj['total_data_size'] + raw_data_size

    if first_packet == True:
        obj['prevUdpRawData'] = currUdpRawData
        return

    prev_raw_data_size = obj['prevUdpRawData'].size

    # frameDataBuff 是个缓冲区，frameDatabuff_index 记录了当前数据的最后一个字节的位置
    obj['frameDataBuff'][obj['frameDataBuff_index']: obj['frameDataBuff_index'] + prev_raw_data_size] = obj[
        'prevUdpRawData']
    obj['frameDataBuff_index'] = obj['frameDataBuff_index'] + prev_raw_data_size
    obj['prevUdpRawData'] = currUdpRawData


def flushLastPacket(obj):
    """
    将滞留在 prevUdpRawData 中的最后一个包写入 buffer，
    以便 fetchNewFramesData 能提取出最后的帧。
    """
    if obj['prevUdpRawData'].size == 0:
        return

    prev_raw_data_size = obj['prevUdpRawData'].size
    obj['frameDataBuff'][obj['frameDataBuff_index']: obj['frameDataBuff_index'] + prev_raw_data_size] = \
        obj['prevUdpRawData']
    obj['frameDataBuff_index'] = obj['frameDataBuff_index'] + prev_raw_data_size
    obj['prevUdpRawData'] = np.array([], dtype=np.uint8)


def getOneUdpPacket(filename, udp_index):
    """
    Args:
        udp_index: where current udp is
    Return:
        flag = 1:  成功读取当前udp_index所指位置的数据包
        flag = -1: 无法检测到当前或下个udp包的起始位置
        flag = 0: 没有读到任何数据包
    Disp:
        read one udp packet data from the given file
    """
    currUdpData = 0
    udp_index += 1
    udp_index = np.int64(udp_index)
    flag = 0

    fsize = os.path.getsize(filename)  # 获取文件的大小（字节）

    if udp_index > (fsize - 2000):
        prefix = np.array([], dtype=np.uint8)
        return flag, udp_index, currUdpData, prefix

    # 从所给文件中以uint8的格式读取count个数据
    startCodeArray = np.fromfile(filename, dtype=np.uint8, count=4, offset=udp_index)

    # 判断是否为udp包的开始。[3, 2, 8, 0] 是recvUDPdata.py中定义的
    if np.sum(np.equal(startCodeArray, [3, 2, 8, 0])) == 4:
        # 之后的两个字节记录了整个UDP包的长度
        pl_Array = np.fromfile(filename, dtype=np.uint8, count=2, offset=udp_index + 4)
        packet_length = int(pl_Array[0]) + int(pl_Array[1]) * 256

        # [3, 2, 8, 0] 和udp 包的长度共同组成了prefix
        prefix = np.concatenate((np.array([3, 2, 8, 0], dtype=np.uint8), pl_Array))

        # 读取写一个自定义的udp_header, 6 = 4(udp header + packet_len)
        startCodeNextArray = np.fromfile(filename, dtype=np.uint8, count=4, offset=udp_index + packet_length + 6)
        if np.sum(np.equal(startCodeNextArray, [3, 2, 8, 0])) == 4:

            # 如果检测到下一个[3, 2, 8, 0], 则读取当前的udp数据
            currUdpData = np.fromfile(filename, dtype=np.uint8, count=packet_length, offset=udp_index + 6)

            # 更新udp_index
            udp_index += packet_length + 5
            flag = 1

        else:
            flag = -1
    else:
        flag = -1

    return flag, udp_index, currUdpData, prefix





def radar_process_frame(radarObj, timeDomainData):
    """
    Args:
        radarObj: configuration of radar
        timeDomainData: total data of a frame
    Disp:
        transfer frame data into data cube with size [numChirpsFrame, numRxChan, numAdcSamples]

    AWR2944P non-interleave, real-only ADC:
        CBUFF format: chirp0{rx0[s0..sN], rx1[s0..sN], ...}, chirp1{...}
        C-order reshape correctly maps this layout.
    """
    numAdcSamples = radarObj['numAdcSamples']
    numRxChan = radarObj['numRxChan']
    numChirpsPerFrame = radarObj['numChirpsPerFrame']
    

    frame_real = np.reshape(timeDomainData, (numChirpsPerFrame, numRxChan, numAdcSamples))
    return frame_real




def radar_range_doppler_fft(frame_data, radarObj,
                             window_range='hanning', window_doppler='hanning'):
    """
    对单帧 raw ADC data 做 2D FFT：Range FFT + Doppler FFT

    Args:
        frame_data: A frame. Shape (numChirpsPerFrame, numRxChan, numAdcSamples), int16
        radarObj: radar configuration dict (需含 range_fftsize, doppler_fftsize 等)
        window_range:  range 维加窗类型 ('hanning' / 'hamming' / None)
        window_doppler: doppler 维加窗类型

    Returns:
        rd_map: shape (doppler_fftsize, numRxChan, range_fftsize // 2), float32
                Range-Doppler magnitude map (仅正半轴, 未做 fftshift)
    """
    numChirpsPerFrame = radarObj['numChirpsPerFrame']
    numRxChan = radarObj['numRxChan']
    numAdcSamples = radarObj['numAdcSamples']
    range_fftsize = radarObj['range_fftsize']
    doppler_fftsize = radarObj['doppler_fftsize']


    # int16 → float32 以便加窗和 FFT
    data = frame_data.astype(np.float32)  # (chirps, rx, adc_samples)

    # -------- Range FFT (沿 adc samples 轴, axis=2) --------
    if window_range == 'hanning':
        win = np.hanning(numAdcSamples).astype(np.float32)
    elif window_range == 'hamming':
        win = np.hamming(numAdcSamples).astype(np.float32)
    else:
        win = np.ones(numAdcSamples, dtype=np.float32)
    data = data * win[None, None, :]

    # Range FFT 带 zero-padding
    range_fft = np.fft.fft(data, n=range_fftsize, axis=2)  # (chirps, rx, range_fftsize)
    # 实数输入 → 仅保留正半轴（舍弃负频率镜像）
    range_fft = range_fft[:, :, :range_fftsize // 2]        # (chirps, rx, range_fftsize//2)


    # -------- Doppler FFT (沿 chirps 轴, axis=0) --------
    if window_doppler == 'hanning':
        win = np.hanning(numChirpsPerFrame).astype(np.float32)
    elif window_doppler == 'hamming':
        win = np.hamming(numChirpsPerFrame).astype(np.float32)
    else:
        win = np.ones(numChirpsPerFrame, dtype=np.float32)
    range_fft = range_fft * win[:, None, None]

    # Doppler FFT 带 zero-padding
    rd_fft = np.fft.fft(range_fft, n=doppler_fftsize, axis=0)  # (doppler, rx, range)

    # 取幅度
    rd_map = np.abs(rd_fft)
    return rd_map


def compute_radar_axes(config_set, range_fftsize, doppler_fftsize):
    """
    从 JSON config 中提取雷达参数，计算物理坐标轴（距离 / 速度）

    Args:
        config_set: JSON config dict
        range_fftsize: range FFT 点数
        doppler_fftsize: Doppler FFT 点数

    Returns:
        range_axis:    shape (range_fftsize,), 单位 m
        velocity_axis: shape (doppler_fftsize,), 单位 m/s（fftshift 后零速居中）
    """
    c = 3e8

    profile = config_set['mmWaveDevices'][0]['rfConfig']['rlProfiles'][0]['rlProfileCfg_t']
    frame_cfg = config_set['mmWaveDevices'][0]['rfConfig']['rlFrameCfg_t']
    chirps = config_set['mmWaveDevices'][0]['rfConfig'].get('rlChirps', [])

    # -------- 起始频率 (Hz) --------
    fc_mhz = profile.get('startFreqConst_MHz', None)
    if fc_mhz is None:
        fc_ghz = profile.get('startFreqConst_GHz', 77.0)
        fc_mhz = fc_ghz * 1e3
    fc = fc_mhz * 1e6

    # -------- 调频斜率 (Hz/s) --------
    slope = profile.get('freqSlopeConst_MHz_per_usec', None)
    if slope is None:
        slope = profile.get('freqSlopeConst_KHz_per_usec', 50000) * 1e-3  # KHz/μs → MHz/μs
    S = slope * 1e12  # MHz/μs → Hz/s

    # -------- ADC 采样率 (Hz) --------
    adc_rate = profile.get('digOutSampleRate', 10000)  # ksps, 默认 10 Msps
    Fs = adc_rate * 1e3  # ksps → Hz

    # -------- 距离轴: R(k) = k * c * Fs / (2 * S * N_fft) (仅正半轴) --------
    num_range_bins = range_fftsize // 2
    range_axis = np.arange(num_range_bins) * c * Fs / (2.0 * S * range_fftsize)

    # -------- 速度轴 --------
    # Chirp 周期 = 空闲时间 + ramp 结束时间
    idle_time = profile.get('idleTimeConst_usec', 7)
    ramp_end = profile.get('rampEndTime_usec', 60)

    if chirps and len(chirps) > 0:
        chip_cfg = chirps[0].get('rlChirpCfg_t', {})
        idle_time += chip_cfg.get('idleTimeVar_usec', 0)

    chirp_period_us = idle_time + ramp_end      # μs
    Tc = chirp_period_us * 1e-6                  # s
    PRF = 1.0 / Tc                               # Hz

    wavelength = c / fc
    # v_max_unambiguous = wavelength * PRF / 4
    velocity_per_bin = wavelength * PRF / (2.0 * doppler_fftsize)

    # fftshift：bin 中心对应零速
    velocity_axis = (np.arange(doppler_fftsize) - doppler_fftsize / 2) * velocity_per_bin

    return range_axis, velocity_axis


def init_rd_display(radarObj, range_axis=None, velocity_axis=None):
    """
    初始化 Range-Doppler 实时显示窗口（单图，合并所有 Rx 通道）

    Args:
        radarObj:      radar configuration dict
        range_axis:    距离轴 (m), shape (range_fftsize,); 为 None 时用 bin 索引
        velocity_axis: 速度轴 (m/s), shape (doppler_fftsize,), 已 fftshift; 为 None 时用 bin 索引

    Returns:
        fig, im: matplotlib figure 和单个 imshow artist
    """
    import matplotlib.pyplot as plt

    doppler_fftsize = radarObj['doppler_fftsize']
    if range_axis is not None:
        num_range_bins = len(range_axis)
    else:
        num_range_bins = radarObj['range_fftsize']

    # 确定 extent: [left, right, bottom, top]
    if range_axis is not None and velocity_axis is not None:
        extent = [range_axis[0], range_axis[-1],
                  velocity_axis[0], velocity_axis[-1]]
        xlabel, ylabel = 'Distance (m)', 'Velocity (m/s)'
    else:
        extent = None
        xlabel, ylabel = 'Range bin', 'Doppler bin'

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(
        np.zeros((doppler_fftsize, num_range_bins)),
        aspect='auto', origin='lower', cmap='jet',
        extent=extent)
    ax.set_title('Range-Doppler')
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    plt.colorbar(im, ax=ax)

    plt.tight_layout()
    plt.ion()
    plt.show()

    return fig, im


def update_rd_display(rd_map, im):
    """
    用新一帧的 RD map 刷新显示（dB 坐标，Doppler fftshift 到中心）
    将所有 Rx 通道合并为单个 RD 图

    Args:
        rd_map: shape (doppler_fftsize, numRxChan, range_fftsize), float32
        im: 单个 imshow artist from init_rd_display()
    """
    import matplotlib.pyplot as plt

    # 只取 Rx1 通道
    rd_rx1 = rd_map[:, 0, :]  # (doppler_fftsize, range_fftsize)
    # 转 dB，加小量避免 log(0)
    rd_db = 20 * np.log10(rd_rx1 + 1e-10)
    # fftshift Doppler 维，使零多普勒居中
    rd_db = np.fft.fftshift(rd_db, axes=0)

    im.set_data(rd_db)
    vmin = rd_db.min()
    vmax = rd_db.max()
    im.set_clim(vmin=vmin, vmax=vmax)

    plt.pause(0.01)


def process_data(filename, json_file_path, radar_info, show_rd=False):
    """
    filename: udp data file path
    json_file_path: path to the mmwave.json config file
    radar_info: configuration of radars
    """

    # 打开 JSON 文件
    with open(json_file_path, "r", encoding="utf-8") as f:
        config_set = json.load(f)

    raw_frames_data = np.array([])
    rd_maps = np.array([])  # 存储每帧的 2D FFT 结果 (Range-Doppler map)
    udp_index = -1
    frame_num = 0
    udpPacketObj = {}
    udpPacketObj['total_data_size'] = 0
    udpPacketObj['frameDataBuff_index'] = 0                               # to indicate where current position is
    udpPacketObj['frameDataBuff'] = np.empty(1000000000, dtype=np.uint8)  # a buffer to store raw udp data
    udpPacketObj['prevUdpRawData'] = np.array([], dtype=np.uint8)

    radarObj_azi = radar_info['radarObj']
    # AWR2944P 输出实数 ADC，每个 sample 占 2 字节 (int16)
    radarObj_azi['gAdcOneSampleSize'] = 2
    radarObj_azi['numAdcSamples'] = config_set['mmWaveDevices'][0]['rfConfig']['rlProfiles'][0]['rlProfileCfg_t']['numAdcSamples']
    radarObj_azi['numRxChan'] = 4
    radarObj_azi['numChirpsPerFrame'] = config_set['mmWaveDevices'][0]['rfConfig']['rlFrameCfg_t']['numLoops']
    radarObj_azi['nChirpsIn1Loop'] = 1

    radarObj_azi['range_fftsize'] = 512
    radarObj_azi['doppler_fftsize'] = 512
    radarObj_azi['angle_fftsize'] = 512

    # -------- 初始化 RD 实时显示 --------
    rd_im = None
    if show_rd:
        range_axis, velocity_axis = compute_radar_axes(
            config_set, radarObj_azi['range_fftsize'], radarObj_azi['doppler_fftsize'])
        print(f"距离分辨率: {range_axis[1] - range_axis[0]:.3f} m, "
              f"最大不模糊距离: {range_axis[-1]:.2f} m")
        print(f"速度分辨率: {velocity_axis[1] - velocity_axis[0]:.3f} m/s, "
              f"最大不模糊速度: ±{velocity_axis[-1]:.2f} m/s")
        rd_fig, rd_im = init_rd_display(radarObj_azi, range_axis, velocity_axis)

    #---------------------------construct radar data cube-----------------------------------#
    # AWR2944P 仅支持实数数据格式, dtype 应为 float（后续信号处理用）
    radarObj_azi['frameComplex'] = np.zeros(
        (radarObj_azi['numChirpsPerFrame'], radarObj_azi['numRxChan'], radarObj_azi['numAdcSamples']), dtype=float)

    dataSizeOneChirp = radarObj_azi['gAdcOneSampleSize'] * radarObj_azi['numAdcSamples'] * radarObj_azi['numRxChan']
    dataSizeOneFrame = dataSizeOneChirp * radarObj_azi['numChirpsPerFrame']

    udpPacketObj['oneFrameDataSize'] = dataSizeOneFrame
    udpPacketObj['frameId'] = 0
    udpPacketObj['zeroPadding'] = np.zeros(dataSizeOneFrame, dtype=np.uint8, order='C')

    seqRatio = np.array([1, 256, 256 << 8, 256 << 16], dtype=np.uint32)  # [1, 256, 65536, 16777216]
    recv_bytes = 0  # record total bytes of received udp data

    print('读取文件:', filename)
    expected_seq_num = 1
    del_frame_index = []  # 记录因丢包而损坏的 frameId

    # 持续从所给文件中读取udp数据
    while True:
        flag, udp_index, currUdpPacketData, prefix = getOneUdpPacket(filename, udp_index)
        if flag == 0:
            break
        elif flag == -1:
            continue

        currSeqNumArray = currUdpPacketData[0:4]
        currSeqNum = np.matmul(currSeqNumArray, seqRatio)  # 提取占据4个字节的序列号
        recv_bytes += len(currUdpPacketData)

        if len(currUdpPacketData) != 1466:
            print(len(currUdpPacketData))

        first_packet = False

        # 如果一个包既不是第一个到达的数据包，而且它的序列号也不是期望的序列号，说明出现丢包
        if currSeqNum != expected_seq_num and (currSeqNum != 1):
            print("misorder: ", [currSeqNum - (currSeqNum - expected_seq_num), currSeqNum])

            missing_packets = currSeqNum - expected_seq_num
            print("missing_packets:", missing_packets)

            # 用零填充替代丢失的数据包（而非复制有效包的 ADC 数据）
            for _ in range(missing_packets):
                dynamic_zero_padding = np.zeros(len(currUdpPacketData), dtype=np.uint8)

                # 将expected_seq_num拆成4字节的小端序
                missing_seq_num_array = np.array(
                    [(expected_seq_num & 0x000000FF),
                     (expected_seq_num & 0x0000FF00) >> 8,
                     (expected_seq_num & 0x00FF0000) >> 16,
                     (expected_seq_num & 0xFF000000) >> 24],
                    dtype=np.uint8)
                dynamic_zero_padding[0:4] = missing_seq_num_array
                # 设置 dataSizeTransed 字段为非零值，防止 readOneUdpPacket 提前返回
                dynamic_zero_padding[4:10] = 1

                last_seq_num = expected_seq_num
                expected_seq_num = expected_seq_num + 1
                readOneUdpPacket(udpPacketObj, dynamic_zero_padding, first_packet)
                flag, newFramesData, newFrameIndex = fetchNewFramesData(udpPacketObj)

            last_seq_num = expected_seq_num
            expected_seq_num = expected_seq_num + 1
            readOneUdpPacket(udpPacketObj, currUdpPacketData, first_packet)
            flag, newFramesData, newFrameIndex = fetchNewFramesData(udpPacketObj)

            # 标记因丢包而损坏的帧
            if udpPacketObj["frameId"] not in del_frame_index:
                del_frame_index.append(udpPacketObj["frameId"])
        else:
            if currSeqNum == 1:
                first_packet = True

            expected_seq_num += 1
            last_seq_num = currSeqNum
            readOneUdpPacket(udpPacketObj, currUdpPacketData, first_packet)
            flag, newFramesData, newFrameIndex = fetchNewFramesData(udpPacketObj)

        # 如果成功读取到udp数据包
        if flag == 1:
            frame_num = frame_num + 1
            n_frames = newFrameIndex.size
            # print("current frame num:", frame_num)
            for ii in range(0, n_frames):
                # 跳过因丢包而损坏的帧
                if newFrameIndex[ii] in del_frame_index:
                    continue

                raw_frame_data = radar_process_frame(radarObj_azi, newFramesData[ii])
                if raw_frames_data.size == 0:
                    raw_frames_data = np.array([raw_frame_data])
                else:
                    raw_frames_data = np.concatenate((raw_frames_data, raw_frame_data[None, :]))

                # 计算当前帧的 Range-Doppler map
                rd_map = radar_range_doppler_fft(raw_frame_data, radarObj_azi)
                if rd_maps.size == 0:
                    rd_maps = np.array([rd_map])
                else:
                    rd_maps = np.concatenate((rd_maps, rd_map[None, :]))

                # 实时刷新显示
                if rd_im is not None:
                    update_rd_display(rd_map, rd_im)

    # ----- 循环结束后，flush 最后一个滞留在 prevUdpRawData 中的包 -----
    flushLastPacket(udpPacketObj)
    flag, newFramesData, newFrameIndex = fetchNewFramesData(udpPacketObj)
    if flag == 1:
        n_frames = newFrameIndex.size
        for ii in range(0, n_frames):
            if newFrameIndex[ii] in del_frame_index:
                continue
            raw_frame_data = radar_process_frame(radarObj_azi, newFramesData[ii])
            if raw_frames_data.size == 0:
                raw_frames_data = np.array([raw_frame_data])
            else:
                raw_frames_data = np.concatenate((raw_frames_data, raw_frame_data[None, :]))

            # 计算当前帧的 Range-Doppler map
            rd_map = radar_range_doppler_fft(raw_frame_data, radarObj_azi)
            if rd_maps.size == 0:
                rd_maps = np.array([rd_map])
            else:
                rd_maps = np.concatenate((rd_maps, rd_map[None, :]))

            # 实时刷新显示
            if rd_im is not None:
                update_rd_display(rd_map, rd_im)

    return raw_frames_data, rd_maps


if __name__ == "__main__":
    # 路径参数化，方便在不同环境下使用
    # json_file_path = "C:\\Users\\wei\\Desktop\\mm.mmwave.json"
    json_file_path = "D:\\work\\multi_model\\radar_data\\radar_dataAWR2944p.mmwave.json"
    # json_file_path = "D:\\work\\mmRadar\\DataCapture\\AWR2944p.mmwave.json"
    # filename = "D:\\2026_07_21_18_44_14\\test\\udpData.dat"
    filename = "D:\\work\\multi_model\\radar_data\\wave_hand\\test\\udpData.dat"

    radar_info = {}
    radar_info['radarObj'] = {}
    radar_info['data'] = np.array([])
    radar_info['frame_num'] = 0

    radar_adc_data, rd_maps = process_data(filename, json_file_path, radar_info, show_rd=True)
    print("raw ADC data shape:", radar_adc_data.shape)
    print("range-Doppler maps shape:", rd_maps.shape)
