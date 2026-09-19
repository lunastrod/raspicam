import cv2
import numpy as np
import os
# Assume Cam class and other imports are available

class MotionDetector:
    def __init__(self):
        # ORB Detector settings
        self.orb = cv2.ORB_create(nfeatures=5000)
        
        # Brute-Force Matcher for ORB (Hamming distance)
        # We use crossCheck=True here for simplicity and to filter out bad matches 
        # by requiring mutual best match status.
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # Store features from the representative frame of the PREVIOUS cycle
        self.kp_last_cycle = None
        self.des_last_cycle = None
        
        # --- RANSAC & Motion Thresholds ---
        self.MIN_MATCH_COUNT = 15
        # Max distance a point can be from projected background
        self.RANSAC_REPROJECTION_THRESHOLD = 5.0 
        # Number of features that moved to trigger motion
        self.MOTION_OUTLIER_THRESHOLD = 50 

    def setNewFrame(self, burst_file_path: str) -> bool:
        """
        Processes the new video burst, comparing the last frame to the history.

        :param burst_file_path: Path to the saved video burst (.mp4).
        :return: True if motion is detected, False otherwise.
        """
        frames = self._get_burst_frames(burst_file_path)
        if not frames:
            return False

        # --- Use the last frame of the burst as the representative frame ---
        # This frame is the most recent view of the scene.
        current_frame = frames[-1]
        
        # 1. Detect ORB features for the current frame
        kp_current, des_current = self.orb.detectAndCompute(current_frame, None)
        
        # Initialize the history on the first run
        if self.des_last_cycle is None or des_current is None:
            self._update_history(kp_current, des_current)
            print("Detector initialized. Ready for motion.")
            return False

        # --- Frame-to-Frame Motion Detection (Current vs. Last Cycle's Frame) ---
        
        # 2. Match features 
        matches = self.bf.match(self.des_last_cycle, des_current)
        
        if len(matches) < self.MIN_MATCH_COUNT:
            # Not enough reliable features to perform RANSAC
            print(f"Low reliable match count ({len(matches)}). Skipping check.")
            self._update_history(kp_current, des_current)
            return False
            
        # 3. RANSAC for Outlier Detection (Motion Trigger)
        # Extract coordinates of matched points
        src_pts = np.float32([self.kp_last_cycle[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp_current[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        # Find Homography (H) and Mask (Inliers/Outliers)
        H, mask = cv2.findHomography(src_pts, dst_pts, 
                                     cv2.RANSAC, 
                                     self.RANSAC_REPROJECTION_THRESHOLD)
        
        if H is None:
            # This is a critical failure, often from a totally broken feature set
            print("WARNING: RANSAC failed to find a model. Skipping detection for this cycle.")
            self._update_history(kp_current, des_current)
            return False 
        
        # Count the Outliers (points that DID NOT fit the static background model)
        # These outliers represent the features belonging to moving objects.
        mask_list = mask.ravel().tolist()
        outlier_count = mask_list.count(0)
        
        # 4. Trigger Check
        motion_detected = outlier_count > self.MOTION_OUTLIER_THRESHOLD
        
        # You can keep this printout for debugging/tuning the threshold
        print(f"RANSAC Inliers: {mask_list.count(1)}, Outliers: {outlier_count}")

        # 5. Update History
        # The successfully extracted features from the *current* frame become the baseline for the * next* cycle.
        self._update_history(kp_current, des_current)
        
        return motion_detected

    def _update_history(self, kp_current, des_current):
        """Saves the current features as the history for the next iteration."""
        self.kp_last_cycle = kp_current
        self.des_last_cycle = des_current