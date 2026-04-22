import { AudioEvent } from "./events"

type AudioMap = Record<AudioEvent, string[]>

export const harshAudioMap: AudioMap = {
  [AudioEvent.GAME_INTRO]: [
    "/audio/harsh/intro/welcome1.mp3",
    "/audio/harsh/intro/welcome2.mp3"
  ],
  [AudioEvent.GAME_START]: [
    "/audio/harsh/start/lets-begin.mp3"
  ],
  [AudioEvent.PLAYER_TURN]: [
    "/audio/harsh/player-turn/your-move.mp3",
    "/audio/harsh/player-turn/take-your-time.mp3"
  ],
  [AudioEvent.PLAYER_DELAY]: [
    "/audio/harsh/player-delay/ticking.mp3",
    "/audio/harsh/player-delay/this-thing-on.mp3"
  ],
  [AudioEvent.AI_MOVE]: [
    "/audio/harsh/ai-move/learn.mp3",
    "/audio/harsh/ai-move/pressures-on.mp3"
  ],
  [AudioEvent.AI_STRONG_MOVE]: [
    "/audio/harsh/ai-strong-move/did-you-see.mp3"
  ],
  [AudioEvent.AI_KING]: [
    "/audio/harsh/ai-king/king-me.mp3",
    "/audio/harsh/ai-king/kneel.mp3",
    "/audio/harsh/ai-king/long-live.mp3"
  ],
  [AudioEvent.PLAYER_KING]: [
    "/audio/harsh/player-king/impressive.mp3",
    "/audio/harsh/player-king/well-played.mp3"
  ],
  [AudioEvent.PLAYER_MISTAKE]: [
    "/audio/harsh/mistakes/sure.mp3"
  ],
  [AudioEvent.AI_TAUNT]: [
    "/audio/harsh/ai-taunt/that-was-bold1.mp3",
    "/audio/harsh/ai-taunt/that-was-bold2.mp3"
  ],
  [AudioEvent.ENDGAME]: [
    "/audio/harsh/endgame/run-it-back.mp3"
  ],
  [AudioEvent.AI_VICTORY]: [
    "/audio/harsh/ai-victory/game-over.mp3",
    "/audio/harsh/ai-victory/one-job.mp3",
    "/audio/harsh/ai-victory/inevitable.mp3"
  ],
  [AudioEvent.PLAYER_VICTORY]: [
    "/audio/harsh/player-victory/well-played1.mp3",
    "/audio/harsh/player-victory/well-played2.mp3"
  ],
  [AudioEvent.REMATCH_PROMPT]: [
    "/audio/harsh/endgame/run-it-back.mp3"
  ]
}

export const sweetAudioMap: AudioMap = {
  [AudioEvent.GAME_INTRO]: [
    "/audio/sweet/intro/HELLO.wav.wav",
    "/audio/sweet/intro/SYSTEM ONLINE.wav.wav"
  ],
  [AudioEvent.GAME_START]: [
    "/audio/sweet/start/SHOW ME WHAT YOU GOT.wav.wav",
    "/audio/sweet/start/SYSTEM ONLINE.wav.wav"
  ],
  [AudioEvent.PLAYER_TURN]: [
    "/audio/sweet/player-turn/SHOW ME WHAT YOU GOT.wav.wav",
    "/audio/sweet/player-turn/TAKE YOUR TIME.wav.wav"
  ],
  [AudioEvent.PLAYER_DELAY]: [
    "/audio/sweet/player-delay/THINKING.wav.wav",
    "/audio/sweet/player-delay/HUMAN ERROR DETECTED.wav.wav"
  ],
  [AudioEvent.AI_MOVE]: [
    "/audio/sweet/ai-move/MERCY.wav.wav",
    "/audio/sweet/ai-move/MOVES CALCULATED.wav.wav",
    "/audio/sweet/ai-move/NICE TRY, MY TURN.wav.wav",
    "/audio/sweet/ai-move/THINKING.wav.wav"
  ],
  [AudioEvent.AI_STRONG_MOVE]: [
    "/audio/sweet/ai-strong-move/Executing MOVE.wav.wav",
    "/audio/sweet/ai-strong-move/NICE TRY, MY TURN.wav.wav"
  ],
  [AudioEvent.AI_KING]: [
    "/audio/sweet/ai-king/IMPRESSIVE.wav.wav",
    "/audio/sweet/ai-king/IMPROVING...SLOWLY.wav.wav"
  ],
  [AudioEvent.PLAYER_KING]: [
    "/audio/sweet/player-king/IMPRESSIVE.wav.wav",
    "/audio/sweet/player-king/TRAP MOVE.wav.wav"
  ],
  [AudioEvent.PLAYER_MISTAKE]: [
    "/audio/sweet/player-mistake/DETECTS PATTERN.wav.wav"
  ],
  [AudioEvent.AI_TAUNT]: [
    "/audio/sweet/ai-taunt/ALMOST.wav.wav",
    "/audio/sweet/ai-taunt/OOPS.wav.wav",
    "/audio/sweet/ai-taunt/QUESTIONABLE MOVE.wav.wav",
    "/audio/sweet/ai-taunt/SHOW ME WHAT YOU GOT.wav.wav",
    "/audio/sweet/ai-taunt/TRAP MOVE.wav.wav"
  ],
  [AudioEvent.ENDGAME]: [
    "/audio/sweet/endgame/GAME COMPLETE.wav.wav"
  ],
  [AudioEvent.AI_VICTORY]: [
    "/audio/sweet/ai-victory/GAME COMPLETE.wav.wav"
  ],
  [AudioEvent.PLAYER_VICTORY]: [
    "/audio/sweet/player-victory/IMPRESSIVE.wav.wav",
    "/audio/sweet/player-victory/IMPROVING...SLOWLY.wav.wav",
    "/audio/sweet/player-victory/UNPREDICTABLE.wav.wav"
  ],
  [AudioEvent.REMATCH_PROMPT]: [
    "/audio/sweet/endgame/GAME COMPLETE.wav.wav"
  ]
}