import { useCallback, useRef, useState } from "react";
import { AudioEvent } from "../../public/audio/events";
import { audioMap } from "../../public/audio/audioMap";

export function useAudioManager() {
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playAudio = useCallback((event: AudioEvent) => {
    if (isMuted) return;

    const audioFiles = audioMap[event];
    if (!audioFiles || audioFiles.length === 0) return;

    // Randomly select one of the available audio files for variety
    const randomIndex = Math.floor(Math.random() * audioFiles.length);
    const audioFile = audioFiles[randomIndex];

    // Stop any currently playing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    // Create and play new audio
    const audio = new Audio(audioFile);
    audioRef.current = audio;

    audio.play().catch(error => {
      console.warn("Failed to play audio:", error);
    });
  }, [isMuted]);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => !prev);
  }, []);

  return {
    playAudio,
    toggleMute,
    isMuted
  };
}