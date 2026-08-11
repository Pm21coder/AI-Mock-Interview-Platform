'use client';

import { forwardRef, useImperativeHandle, useRef, useState } from 'react';
import Webcam from 'react-webcam';

const VideoRecorder = forwardRef(({ isRecording, onStart, onStop }, ref) => {
  const webcamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const [isRecordingState, setIsRecordingState] = useState(false);

  useImperativeHandle(ref, () => ({
    startRecording: handleStartRecording,
    stopRecording: handleStopRecording,
  }));

  const handleStartRecording = () => {
    if (!webcamRef.current || !webcamRef.current.stream) {
      return;
    }

    recordedChunksRef.current = [];

    const stream = webcamRef.current.stream;
    if (typeof MediaRecorder === 'undefined') {
      onStop(null);
      return;
    }

    const options = MediaRecorder.isTypeSupported?.('video/webm') ? { mimeType: 'video/webm' } : undefined;
    mediaRecorderRef.current = new MediaRecorder(stream, options);
    setIsRecordingState(true);
    onStart();

    mediaRecorderRef.current.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunksRef.current.push(event.data);
      }
    };

    mediaRecorderRef.current.onstop = () => {
      const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
      onStop(blob);
    };

    mediaRecorderRef.current.start();
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecordingState) {
      setIsRecordingState(false);
      mediaRecorderRef.current.stop();
    }
  };

  const videoConstraints = {
    width: 640,
    height: 480,
    facingMode: 'user',
  };

  return (
    <div className="rounded-lg bg-white p-4 shadow-lg">
      <div className="relative">
        <Webcam
          ref={webcamRef}
          audio={true}
          screenshotFormat="image/jpeg"
          videoConstraints={videoConstraints}
          className="w-full rounded-lg"
          onUserMediaError={() => setIsRecordingState(false)}
        />

        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 space-x-4">
          {!isRecordingState ? (
            <button
              onClick={handleStartRecording}
              className="flex items-center gap-2 rounded-full bg-red-600 px-6 py-2 text-white transition hover:bg-red-700"
            >
              <span className="inline-block h-3 w-3 rounded-full bg-white"></span>
              Start Recording
            </button>
          ) : (
            <button
              onClick={handleStopRecording}
              className="rounded-full bg-gray-600 px-6 py-2 text-white transition hover:bg-gray-700"
            >
              Stop Recording
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${isRecordingState ? 'animate-pulse bg-red-600' : 'bg-gray-400'}`}></div>
          <span>{isRecordingState ? 'Recording...' : 'Ready to record'}</span>
        </div>
        <span>Camera: Active</span>
      </div>
    </div>
  );
});

VideoRecorder.displayName = 'VideoRecorder';

export default VideoRecorder;
