# Computer Vision Implementation Guide

**Status**: ⏳ Not yet implemented  
**Priority**: P0 - Enhancement (Does not block core functionality)  
**Estimated Effort**: 2-4 hours  
**Complexity**: Medium

---

## Current State

### What's Simulated ❌

The current implementation uses time-based sine waves to simulate computer vision:

**File**: `frontend/components/VideoRecorder.js` (lines 93-102)

```javascript
// Current: Pure simulation
const eyeContactVal = 88 + Math.sin(Date.now() / 1000) * 8;
const confidenceVal = 90 + Math.cos(Date.now() / 1200) * 6;
const positivityVal = 84 + Math.sin(Date.now() / 1500) * 10;
```

**Result**: Users see "Computer vision analyzing..." but values are fake.

### What Needs to Change ✅

Replace simulation with real MediaPipe face detection that:
1. Tracks actual facial landmarks
2. Detects eye gaze direction (eye contact)
3. Detects facial expressions (smile = positivity)
4. Measures confidence based on expression clarity

---

## Implementation Plan

### Step 1: Install MediaPipe

```bash
cd mock-interview-platform/frontend
npm install @mediapipe/camera_utils @mediapipe/control_utils @mediapipe/drawing_utils @mediapipe/face_landmarker
```

Or with Python backend:
```bash
cd mock-interview-platform/backend
pip install mediapipe opencv-python
```

### Step 2: Frontend Implementation (Recommended)

**File to Modify**: `frontend/components/VideoRecorder.js`

**Current Code (Lines 93-102)**:
```javascript
// Get video element
const video = videoRef.current;

// SIMULATED: Replace this with real MediaPipe code
const eyeContactVal = 88 + Math.sin(Date.now() / 1000) * 8;
const confidenceVal = 90 + Math.cos(Date.now() / 1200) * 6;
const positivityVal = 84 + Math.sin(Date.now() / 1500) * 10;

setMetrics({
  eyeContact: eyeContactVal,
  confidence: confidenceVal,
  positivity: positivityVal,
});
```

**Replace With**:
```javascript
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";

// Initialize FaceLandmarker once
const initializeFaceLandmarker = async () => {
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
  );
  return await FaceLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "https://storage.googleapis.com/mediapipe-models/vision_landmark_detector/face_landmarker/float16/1/face_landmarker.task",
      delegate: "GPU"
    },
    runningMode: "VIDEO",
    numFaces: 1
  });
};

// Call in useEffect
const faceLandmarker = await initializeFaceLandmarker();

// In animation loop:
const detectFace = () => {
  if (!videoRef.current) return;
  
  const results = faceLandmarker.detectForVideo(videoRef.current, Date.now());
  
  if (results.faceLandmarks && results.faceLandmarks[0]) {
    const landmarks = results.faceLandmarks[0];
    
    // Calculate metrics from landmarks
    const eyeContact = calculateEyeContact(landmarks);
    const confidence = calculateConfidence(landmarks);
    const positivity = calculatePositivity(landmarks);
    
    setMetrics({
      eyeContact,
      confidence,
      positivity
    });
  }
  
  requestAnimationFrame(detectFace);
};
```

**Helper Functions**:

```javascript
// Calculate eye contact score (0-100)
// Based on gaze direction and head pose
const calculateEyeContact = (landmarks) => {
  // MediaPipe indices for eye landmarks
  const leftEyeCenter = landmarks[133];  // Left eye center
  const rightEyeCenter = landmarks[362]; // Right eye center
  const noseTip = landmarks[1];          // Nose tip (center reference)
  
  // Calculate distance from eyes to center
  const leftEyeDistance = Math.sqrt(
    Math.pow(leftEyeCenter.x - noseTip.x, 2) +
    Math.pow(leftEyeCenter.y - noseTip.y, 2)
  );
  const rightEyeDistance = Math.sqrt(
    Math.pow(rightEyeCenter.x - noseTip.x, 2) +
    Math.pow(rightEyeCenter.y - noseTip.y, 2)
  );
  
  // Smaller distance = more direct eye contact
  const avgDistance = (leftEyeDistance + rightEyeDistance) / 2;
  const eyeContactScore = Math.max(0, 100 - (avgDistance * 300));
  
  return Math.min(100, Math.round(eyeContactScore));
};

// Calculate confidence score (0-100)
// Based on face visibility and stability
const calculateConfidence = (landmarks) => {
  // Check if landmarks have good z-depth (z > 0.1 is visible)
  const visiblePoints = landmarks.filter(l => l.z && l.z > 0.1).length;
  const visibilityScore = (visiblePoints / landmarks.length) * 100;
  
  // Stability: check if landmarks haven't moved much
  // (would need to track previous frame for full stability)
  const confidenceScore = visibilityScore;
  
  return Math.round(Math.min(100, confidenceScore));
};

// Calculate positivity score (0-100)
// Based on smile detection
const calculatePositivity = (landmarks) => {
  // Mouth corner landmarks
  const leftMouthCorner = landmarks[61];   // Left mouth corner
  const rightMouthCorner = landmarks[291]; // Right mouth corner
  const mouthCenter = landmarks[13];       // Mouth center
  const noseBottom = landmarks[2];         // Nose bottom
  
  // Calculate mouth curvature
  const mouthWidth = Math.abs(rightMouthCorner.x - leftMouthCorner.x);
  const mouthHeight = Math.abs(mouthCenter.y - noseBottom.y);
  const mouthRatio = mouthHeight / (mouthWidth + 0.001);
  
  // Smile detected if mouth curves up (negative y change) and opens
  let positivityScore = 50; // Neutral baseline
  
  if (mouthRatio > 0.3) {
    positivityScore += 30; // Mouth open suggests engagement
  }
  if (leftMouthCorner.y > mouthCenter.y && rightMouthCorner.y > mouthCenter.y) {
    positivityScore += 20; // Smile (mouth corners up)
  }
  
  return Math.round(Math.min(100, positivityScore));
};
```

### Step 3: Backend Implementation (Alternative)

**File**: `backend/app/services/cv_analysis.py`

Currently stubbed out. To enable:

```python
import mediapipe as mp
import cv2
import base64
import io
from PIL import Image
import numpy as np

class ComputerVisionAnalyzer:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detector = self.mp_face_detection.FaceDetection(
            model_selection=0,  # 0 for short-range (~2m), 1 for long-range (~5m)
            min_detection_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def analyze_frame(self, frame_base64: str) -> dict:
        """
        Analyze a single video frame for eye contact, confidence, and positivity.
        
        Args:
            frame_base64: Base64 encoded image data
            
        Returns:
            Dictionary with metrics {eye_contact, confidence, positivity}
        """
        # Decode frame
        frame_data = base64.b64decode(frame_base64)
        frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
        
        if frame is None:
            return self._empty_analysis()
        
        # Detect faces
        results = self.face_detector.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        
        if not results.detections:
            return self._empty_analysis()
        
        detection = results.detections[0]
        
        # Extract metrics
        eye_contact = self._calculate_eye_contact(detection, frame)
        confidence = self._calculate_confidence(detection)
        positivity = self._calculate_positivity(detection, frame)
        
        return {
            'eye_contact': eye_contact,
            'confidence': confidence,
            'positivity': positivity,
            'face_detected': True
        }
    
    def _calculate_eye_contact(self, detection, frame) -> int:
        """Calculate eye contact (0-100) based on head pose and gaze."""
        # Get bounding box
        h, w, _ = frame.shape
        bbox = detection.location_data.relative_bounding_box
        x_center = bbox.xmin + bbox.width / 2
        
        # Score based on horizontal position
        # 0.5 (center) = 100, edges = lower
        center_diff = abs(x_center - 0.5)
        eye_contact = int((1 - center_diff * 2) * 100)
        
        return max(0, min(100, eye_contact))
    
    def _calculate_confidence(self, detection) -> int:
        """Calculate confidence (0-100) based on detection strength."""
        confidence_score = detection.score[0] * 100
        return int(confidence_score)
    
    def _calculate_positivity(self, detection, frame) -> int:
        """Estimate positivity (0-100) based on keypoints."""
        # This would need face landmarks (MediaPipe Face Landmarker)
        # For now, use detection confidence as proxy
        return int(detection.score[0] * 100 * 0.8 + 20)  # 20-100 range
    
    def _empty_analysis(self) -> dict:
        """Return empty analysis when face not detected."""
        return {
            'eye_contact': 0,
            'confidence': 0,
            'positivity': 0,
            'face_detected': False
        }
```

### Step 4: Update API Route

**File**: `backend/app/routes/interview.py`

Current code (lines 150-180):
```python
video_data_provided = data.get('video_data', False)
has_video_feature = subscription_service.has_feature(
    subscription_user_id,
    'video_analysis',
)

if video_data_provided and has_video_feature:
    video_data = data.get('video_data', '')
    cv_feedback = cv_service.analyze_frame(video_data)
else:
    cv_feedback = {}
```

This already supports real video analysis once `cv_service.analyze_frame()` returns real data.

---

## Testing the Implementation

### Test Frontend Implementation

```javascript
// In browser console, test MediaPipe detection:
const testVideo = document.querySelector('video');
const results = await faceLandmarker.detectForVideo(testVideo, Date.now());
console.log('Face landmarks detected:', results.faceLandmarks.length);
console.log('Eye contact:', calculateEyeContact(results.faceLandmarks[0]));
console.log('Confidence:', calculateConfidence(results.faceLandmarks[0]));
console.log('Positivity:', calculatePositivity(results.faceLandmarks[0]));
```

### Test Backend Implementation

```bash
# Create test frame (single frame from webcam)
curl -X POST http://localhost:5000/api/interview/analyze-answer \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about yourself",
    "answer": "I am a software engineer",
    "video_data": "'$(base64 -w0 test_frame.jpg)'"
  }'
```

---

## Performance Considerations

### Frontend (MediaPipe.js)
- **Pros**: Runs on client, no server load, real-time ~30fps
- **Cons**: Larger JS bundle, requires GPU for smooth performance
- **Recommended**: Use for better UX

### Backend (MediaPipe Python)
- **Pros**: Centralized control, can apply ML models
- **Cons**: Server load, processing latency, requires GPU
- **Recommended**: Use for strict audit requirements

### Hybrid Approach
- Run detection frontend for real-time feedback
- Send frames to backend for permanent audit logs
- Best of both worlds!

---

## Fallback Strategy

If MediaPipe initialization fails:
```javascript
try {
  const faceLandmarker = await initializeFaceLandmarker();
  detectFace(); // Use real detection
} catch (error) {
  console.warn("MediaPipe failed, using fallback", error);
  useFallbackSimulation(); // Use sine waves
}
```

---

## Resource Requirements

### Frontend
- Disk space: ~5MB (JavaScript libraries)
- Memory: ~100MB (model + buffers)
- Network: One-time download of 50MB model

### Backend
- Disk space: ~300MB (MediaPipe Python + models)
- Memory: ~500MB per frame analysis
- GPU: Optional but recommended (10-100x faster)

---

## Timeline for Implementation

1. **Phase 1 (30 min)**: Install dependencies
   - `npm install @mediapipe/tasks-vision` (frontend)
   - `pip install mediapipe` (backend - optional)

2. **Phase 2 (1 hour)**: Implement MediaPipe detection
   - Initialize FaceLandmarker
   - Implement helper functions
   - Test with video stream

3. **Phase 3 (30 min)**: Integrate with existing code
   - Replace simulation code
   - Add error handling
   - Test end-to-end

4. **Phase 4 (30 min)**: Testing & optimization
   - Performance optimization
   - Edge case handling
   - Browser compatibility

---

## Known Limitations

1. **Poor lighting**: Accuracy drops in dim environments
2. **Multiple faces**: Only tracks first face detected
3. **Fast motion**: May lose tracking during rapid head movement
4. **Glasses/occlusions**: May affect eye contact detection
5. **Mobile**: May require lower resolution for performance

---

## References

- [MediaPipe Face Landmarker Docs](https://developers.google.com/mediapipe/solutions/vision/face_landmarker)
- [Face Detection Task Guide](https://developers.google.com/mediapipe/solutions/vision/face_detection)
- [FaceLandmarker Face Geometry](https://mediapipe.dev/solutions/face_landmarker#models)

---

## Status: Ready for Implementation

All infrastructure is in place. Computer vision can be added by:
1. Installing MediaPipe
2. Replacing 10 lines of simulation code
3. Testing with real video

**No blocking issues remain.**
