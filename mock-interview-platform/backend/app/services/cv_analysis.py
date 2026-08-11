import cv2
import mediapipe as mp
import numpy as np
from collections import deque


class CVAnalysisService:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_pose = mp.solutions.pose
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose = self.mp_pose.Pose(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.eye_contact_history = deque(maxlen=50)
        self.smile_history = deque(maxlen=50)

    def analyze_frame(self, frame):
        results = {
            'eye_contact': 0,
            'smile': 0,
            'posture': 'good',
            'gestures': 0,
            'confidence': 0,
        }

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_results = self.face_mesh.process(rgb_frame)
        if face_results.multi_face_landmarks:
            results['eye_contact'] = self._analyze_eye_contact(face_results)
            results['smile'] = self._analyze_smile(face_results)

        pose_results = self.pose.process(rgb_frame)
        if pose_results.pose_landmarks:
            results['posture'] = self._analyze_posture(pose_results)
            results['gestures'] = self._analyze_gestures(pose_results)

        results['confidence'] = self._calculate_confidence(results)
        return results

    def _analyze_eye_contact(self, face_results):
        eye_contact_score = 0.6
        self.eye_contact_history.append(eye_contact_score)
        return float(np.mean(self.eye_contact_history))

    def _analyze_smile(self, face_results):
        smile_score = 0.5
        self.smile_history.append(smile_score)
        return float(np.mean(self.smile_history))

    def _analyze_posture(self, pose_results):
        landmarks = pose_results.pose_landmarks.landmark
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        shoulder_diff = abs(left_shoulder.y - right_shoulder.y)

        if shoulder_diff < 0.05:
            return 'good'
        elif shoulder_diff < 0.1:
            return 'fair'
        return 'poor'

    def _analyze_gestures(self, pose_results):
        landmarks = pose_results.pose_landmarks.landmark
        left_hand = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
        right_hand = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]

        gesture_count = 0
        if abs(left_hand.x - 0.5) > 0.2:
            gesture_count += 1
        if abs(right_hand.x - 0.5) > 0.2:
            gesture_count += 1
        return gesture_count

    def _calculate_confidence(self, results):
        weights = {
            'eye_contact': 0.3,
            'smile': 0.2,
            'posture': 0.3,
            'gestures': 0.2,
        }
        posture_score = {'good': 0.8, 'fair': 0.5, 'poor': 0.2}

        confidence = (
            weights['eye_contact'] * results['eye_contact']
            + weights['smile'] * results['smile']
            + weights['posture'] * posture_score.get(results['posture'], 0.5)
            + weights['gestures'] * min(results['gestures'] / 10, 1.0)
        )
        return min(confidence, 1.0)

    def get_video_analysis(self, video_path):
        cap = cv2.VideoCapture(video_path)
        total_frames = 0
        total_confidence = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            results = self.analyze_frame(frame)
            total_confidence += results['confidence']
            total_frames += 1

        cap.release()

        if total_frames > 0:
            avg_confidence = total_confidence / total_frames
            return {
                'average_confidence': avg_confidence,
                'total_frames_analyzed': total_frames,
                'overall_assessment': self._get_overall_assessment(avg_confidence),
            }

        return {
            'average_confidence': 0,
            'total_frames_analyzed': 0,
            'overall_assessment': 'No frames analyzed',
        }

    def _get_overall_assessment(self, avg_confidence):
        if avg_confidence > 0.7:
            return 'Excellent confidence and presence'
        if avg_confidence > 0.5:
            return 'Good confidence, could improve further'
        return 'Needs improvement in confidence and body language'
