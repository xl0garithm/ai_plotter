import { useCallback, useRef, useState } from "react";
import { AudioEvent } from "../../public/audio/events";
import { harshAudioMap, sweetAudioMap } from "../../public/audio/audioMap";

export type VoiceStyle = "harsh" | "sweet";

export function useAudioManager(voiceStyle: VoiceStyle = "harsh") {
  const [isMuted, setIsMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const playAudio = useCallback((event: AudioEvent) => {
    if (isMuted) return;

    const audioMap = voiceStyle === "sweet" ? sweetAudioMap : harshAudioMap;
    const audioFiles = audioMap[event];
    if (!audioFiles || audioFiles.length === 0) return;

    const randomIndex = Math.floor(Math.random() * audioFiles.length);
    const audioFile = audioFiles[randomIndex];

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }

    const audio = new Audio(audioFile);
    audioRef.current = audio;

    audio.play().catch(error => {
      console.warn("Failed to play audio:", error);
    });
  }, [isMuted, voiceStyle]);

  const toggleMute = useCallback(() => {
    setIsMuted(prev => !prev);
  }, []);

  return { playAudio, toggleMute, isMuted };
}