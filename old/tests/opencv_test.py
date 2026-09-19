import cv2
import numpy as np

def motion_detector(img1,img2):
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    cv2.imshow("img1", gray1)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    cv2.imshow("img2", gray2)
    frame_delta = cv2.absdiff(gray1, gray2)
    cv2.imshow("frame_delta", frame_delta)
    thresh = cv2.threshold(frame_delta, 75, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    cv2.imshow("thresh", thresh)

    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(contours)

if __name__ == "__main__":
    img1=cv2.imread("C:\Astrod\Programacion\DAM-general\Varios\RaspiCam\img\img21.jpg")
    img2=cv2.imread("C:\Astrod\Programacion\DAM-general\Varios\RaspiCam\img\img22.jpg")

    motion_detector(img1,img2)
    cv2.waitKey()


