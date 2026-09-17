#!/usr/bin/env python3

import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime

pipeline = dai.Pipeline()
monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
stereo = pipeline.create(dai.node.StereoDepth)

# Linking
monoLeftOut = monoLeft.requestFullResolutionOutput()
monoRightOut = monoRight.requestFullResolutionOutput()
monoLeftOut.link(stereo.left)
monoRightOut.link(stereo.right)

stereo.setRectification(True)
stereo.setExtendedDisparity(True)
stereo.setLeftRightCheck(True)

disparityQueue = stereo.disparity.createOutputQueue()


with pipeline:
    pipeline.start()
    ts_file = open("frame_timestamps.txt", "w")
    startTime = time.time()
    maxDisparity = 1
    frame_idx = 0
    first_abs = None
    last_abs = None
    try:
        while pipeline.isRunning():
            disparity = disparityQueue.get()
            ts = time.time() - startTime
            ts_file.write(f"{frame_idx}: {ts:.6f}\n")
            ts_file.flush()
            frame_idx += 1
            now = datetime.now()
            if first_abs is None:
                first_abs = now
            last_abs = now
            assert isinstance(disparity, dai.ImgFrame)
            npDisparity = disparity.getFrame()
            maxDisparity = max(maxDisparity, np.max(npDisparity))
            scaled = ((npDisparity / maxDisparity) * 255).astype(np.uint8)
            colorizedDisparity = cv2.applyColorMap(scaled, cv2.COLORMAP_JET)
            colorizedDisparity[npDisparity == 0] = [0, 0, 0]
            cv2.imshow("disparity", colorizedDisparity)
            key = cv2.waitKey(1)
            if key == ord('q'):
                pipeline.stop()
                break
    finally:
        if first_abs is not None:
            ts_file.write(f"\nfirst_frame: {first_abs.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
            ts_file.write(f"last_frame:  {last_abs.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
            ts_file.flush()
        ts_file.close()
