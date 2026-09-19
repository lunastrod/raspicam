import cv2
import numpy as np

backSub = cv2.createBackgroundSubtractorMOG2(history=20, varThreshold=35, detectShadows=False)

def motion_detector(img1,img2):
    backSub.

if __name__ == "__main__":
    img1=cv2.imread("C:\Astrod\Programacion\DAM-general\Varios\RaspiCam\img\img21.jpg")
    img2=cv2.imread("C:\Astrod\Programacion\DAM-general\Varios\RaspiCam\img\img22.jpg")
    
    motion_detector(img1,img2)
    cv2.waitKey()