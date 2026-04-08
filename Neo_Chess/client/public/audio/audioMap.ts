import { AudioEvent } from "./events"

export const audioMap: Record<AudioEvent, string[]> = {
  [AudioEvent.GAME_INTRO]: [
    "/audio/intro/welcome1.mp3",
    "/audio/intro/welcome2.mp3"
  ],

  [AudioEvent.GAME_START]: [
    "/audio/start/lets-begin.mp3"
  ],

  [AudioEvent.PLAYER_TURN]: [
    "/audio/player-turn/your-move.mp3",
    "/audio/player-turn/take-your-time.mp3"
  ],

  [AudioEvent.PLAYER_DELAY]: [
    "/audio/player-delay/ticking.mp3",
    "/audio/player-delay/this-thing-on.mp3"
  ],

  [AudioEvent.AI_MOVE]: [
    "/audio/ai-move/learn.mp3",
    "/audio/ai-move/pressures-on.mp3"
  ],

  [AudioEvent.AI_STRONG_MOVE]: [
    "/audio/ai-strong-move/did-you-see.mp3"
  ],

  [AudioEvent.AI_KING]: [
    "/audio/ai-king/king-me.mp3",
    "/audio/ai-king/kneel.mp3",
    "/audio/ai-king/long-live.mp3"
  ],

  [AudioEvent.PLAYER_KING]: [
    "/audio/player-king/impressive.mp3",
    "/audio/player-king/well-played.mp3"
  ],

  [AudioEvent.PLAYER_MISTAKE]: [
    "/audio/mistakes/sure.mp3"
  ],

  [AudioEvent.AI_TAUNT]: [
    "/audio/ai-taunt/that-was-bold1.mp3",
    "/audio/ai-taunt/that-was-bold2.mp3"
  ],

  [AudioEvent.ENDGAME]: [

    "/audio/endgame/run-it-back.mp3"
  ],

  [AudioEvent.AI_VICTORY]: [
    "/audio/ai-victory/game-over.mp3",
    "/audio/ai-victory/one-job.mp3",
    "/audio/ai-victory/inevitable.mp3"
  ],

  [AudioEvent.PLAYER_VICTORY]: [
    "/audio/player-victory/well-played1.mp3",
    "/audio/player-victory/well-played2.mp3"
  ],

  [AudioEvent.REMATCH_PROMPT]: [
    "/audio/endgame/run-it-back.mp3"
  ]
}