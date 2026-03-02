import { Chess } from "chess.js";

// Piece values for basic evaluation
const pieceValues: Record<string, number> = {
  p: 10,
  n: 30,
  b: 30,
  r: 50,
  q: 90,
  k: 900,
};

/**
 * Very basic 1-ply chess AI.
 * It looks at all legal moves and picks one that captures the most valuable piece,
 * with some random noise to ensure games aren't identical every time.
 */
export function makeAIMove(game: Chess): string | null {
  const moves = game.moves({ verbose: true });
  if (moves.length === 0) return null;

  let bestMove = moves[0];
  let bestScore = -Infinity;

  for (const move of moves) {
    let score = 0;
    
    // Evaluate capture
    if (move.captured) {
      // Gain value of captured piece, subtract a fraction of the capturing piece's value 
      // (encourages taking high value pieces with low value pieces)
      score += pieceValues[move.captured] - (pieceValues[move.piece] * 0.1);
    }
    
    // Evaluate promotion
    if (move.promotion) {
      score += pieceValues[move.promotion];
    }

    // Add slight randomness (0 to 5 points) so the AI doesn't always play exactly the same game
    score += Math.random() * 5;

    // Favor moves towards the center slightly
    const isCenter = ['d4', 'd5', 'e4', 'e5'].includes(move.to);
    if (isCenter) score += 2;

    if (score > bestScore) {
      bestScore = score;
      bestMove = move;
    }
  }

  return bestMove.san;
}
