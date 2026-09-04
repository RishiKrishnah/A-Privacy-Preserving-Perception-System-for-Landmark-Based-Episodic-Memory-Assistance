Model weights are intentionally not bundled.

You may place YOLO-World weights here, for example:

weights/yolov8s-world.pt

and set:

perception:
  model: weights/yolov8s-world.pt

The MediaPipe hand model is downloaded automatically to:
data/hand_landmarker.task
