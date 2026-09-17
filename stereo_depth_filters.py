#!/usr/bin/env python3

import argparse
import random
import os
import cv2
import depthai as dai
import numpy as np
import time
from datetime import datetime

FPS = 20

def getRandomMedianFilterParams():
    return random.choice(
        [
            dai.node.ImageFilters.MedianFilterParams.MEDIAN_OFF,
            dai.node.ImageFilters.MedianFilterParams.KERNEL_3x3,
            dai.node.ImageFilters.MedianFilterParams.KERNEL_5x5,
        ]
    )


def getRandomTemporalFilterParams():
    params = dai.node.ImageFilters.TemporalFilterParams()
    params.enable = random.choice([True, False])
    params.persistencyMode = random.choice(
        [
            dai.filters.params.TemporalFilter.PersistencyMode.PERSISTENCY_OFF,
            dai.filters.params.TemporalFilter.PersistencyMode.VALID_2_IN_LAST_4,
            dai.filters.params.TemporalFilter.PersistencyMode.VALID_1_IN_LAST_2,
            dai.filters.params.TemporalFilter.PersistencyMode.VALID_1_IN_LAST_8,
            dai.filters.params.TemporalFilter.PersistencyMode.PERSISTENCY_INDEFINITELY,
        ]
    )
    params.alpha = random.uniform(0.3, 0.9)
    return params


def getRandomSpeckleFilterParams():
    params = dai.node.ImageFilters.SpeckleFilterParams()
    params.enable = random.choice([True, False])
    return params


def getRandomSpatialFilterParams():
    params = dai.node.ImageFilters.SpatialFilterParams()
    params.enable = random.choice([True, False])
    return params


def main(args: argparse.Namespace):
    # Create pipeline
    with dai.Pipeline() as pipeline:
        monoLeft = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_B)
        monoRight = pipeline.create(dai.node.Camera).build(dai.CameraBoardSocket.CAM_C)
        outLeft = monoLeft.requestOutput((640, 400), fps=FPS)
        outRight = monoRight.requestOutput((640, 400), fps=FPS)

        depth = pipeline.create(dai.node.StereoDepth)

        filterPipeline = pipeline.create(dai.node.ImageFilters)
        filterFactories = [
            getRandomSpeckleFilterParams,
            getRandomTemporalFilterParams,
            getRandomSpatialFilterParams,
            getRandomMedianFilterParams,
        ]

        filterPipeline.setRunOnHost(True)

        depth.setLeftRightCheck(args.lr_check)
        depth.setExtendedDisparity(args.extended_disparity)
        depth.setSubpixel(args.subpixel)
        depth.inputConfig.setBlocking(False)

        # Linking
        outLeft.link(depth.left)
        outRight.link(depth.right)

        # disparity 输出只建一个消费队列（避免双消费者冲突）
        depthQueue = depth.disparity.createOutputQueue()

        # ImageFilters 不再通过 build(depth.disparity) 直接绑定 disparity，
        # 而是在主循环中手动将 disparity 帧送入 input queue
        filterPipeline.build()

        ## Create a new filter pipeline
        filterPipeline.initialConfig.filterIndices = []
        filterPipeline.initialConfig.filterParams = [
            filterFactory() for filterFactory in filterFactories
        ]

        configInputQueue = filterPipeline.inputConfig.createInputQueue()
        filterInputQueue = filterPipeline.input.createInputQueue()
        filterOutputQueue = filterPipeline.output.createOutputQueue()

        pipeline.start()
        currentTime = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        frames_dir = f"{currentTime}_frames"
        os.makedirs(os.path.join(frames_dir, "raw"), exist_ok=True)
        os.makedirs(os.path.join(frames_dir, "color"), exist_ok=True)
        os.makedirs(os.path.join(frames_dir, "filtered"), exist_ok=True)
        ts_file = open(os.path.join(frames_dir, "frame_timestamps.txt"), "w")
        startTime = time.time()
        frame_idx = 0
        first_abs = None
        last_abs = None
        tSwitch = time.time()

        # 先获取第一帧并送入 filter，避免 filterOutputQueue.get() 在首次迭代时阻塞
        inDisparity: dai.ImgFrame = depthQueue.get()
        filterInputQueue.send(inDisparity)

        try:
            while pipeline.isRunning():
                ts = time.time() - startTime
                ts_file.write(f"{frame_idx}: {ts:.6f}\n")
                ts_file.flush()
                now = datetime.now()
                if first_abs is None:
                    first_abs = now
                    ts_file.write(f"first_frame: {first_abs.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                    ts_file.flush()
                last_abs = now
                frame = inDisparity.getFrame()
                filterFrame = filterOutputQueue.get()
                filterFrame = (
                    filterFrame.getFrame() * (255 / depth.initialConfig.getMaxDisparity())
                ).astype(np.uint8)
                frame = (frame * (255 / depth.initialConfig.getMaxDisparity())).astype(
                    np.uint8
                )
                cv2.imwrite(os.path.join(frames_dir, "raw", f"frame_{frame_idx:05d}.png"), frame)
                cv2.imshow("disparity", frame)
                colorFrame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)
                cv2.imwrite(os.path.join(frames_dir, "color", f"frame_{frame_idx:05d}.png"), colorFrame)
                cv2.imshow("disparity_color", colorFrame)
                filteredColorFrame = cv2.applyColorMap(filterFrame, cv2.COLORMAP_JET)
                cv2.imwrite(os.path.join(frames_dir, "filtered", f"frame_{frame_idx:05d}.png"), filteredColorFrame)
                cv2.imshow("filtered_disparity_color", filteredColorFrame)

                frame_idx += 1

                ## Get next frame and feed to filter
                inDisparity = depthQueue.get()
                filterInputQueue.send(inDisparity)

                ## Update filter pipeline
                if time.time() - tSwitch > 1.0:
                    index = random.randint(0, len(filterFactories) - 1)
                    new_params = filterFactories[index]()
                    config = dai.ImageFiltersConfig().updateFilterAtIndex(
                        index, new_params
                    )
                    configInputQueue.send(config)
                    tSwitch = time.time()
                    print(f"Filter at index {index} changed to {new_params}")

                key = cv2.waitKey(1)
                if key == ord("q"):
                    break
        finally:
            if first_abs is not None:
                ts_file.write(f"\nfirst_frame: {first_abs.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                ts_file.write(f"last_frame:  {last_abs.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                ts_file.flush()
            ts_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extended_disparity", action="store_true", help="Use extended disparity"
    )
    parser.add_argument("--subpixel", action="store_true", help="Use subpixel")
    parser.add_argument("--lr_check", action="store_true", help="Use left-right check")
    args = parser.parse_args()
    main(args)
