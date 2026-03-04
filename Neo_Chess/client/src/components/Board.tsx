import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, ContactShadows, Environment } from "@react-three/drei";
import * as THREE from "three";
import { Chess } from "chess.js";
import { ChessGameState } from "@/hooks/use-chess-engine";

interface BoardProps {
  gameState: ChessGameState;
  onSquareClick: (square: string) => void;
  viewMode?: "white" | "black" | "top";
}

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];
const RANKS = ["8", "7", "6", "5", "4", "3", "2", "1"];
const TILE_SIZE = 1;

function squareToXZ(square: string): [number, number] {
  const file = square.charCodeAt(0) - 97;
  const rank = 8 - parseInt(square[1]);
  const x = (file - 3.5) * TILE_SIZE;
  const z = (rank - 3.5) * TILE_SIZE;
  return [x, z];
}

// Chess piece components using Three.js primitives
function PawnMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  return (
    <group>
      <mesh position={[0, 0.1, 0]} castShadow>
        <cylinderGeometry args={[0.28, 0.32, 0.12, 16]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.2} metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.22, 0]} castShadow>
        <cylinderGeometry args={[0.14, 0.18, 0.15, 12]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.2} metalness={0.8} roughness={0.2} />
      </mesh>
      <mesh position={[0, 0.36, 0]} castShadow>
        <sphereGeometry args={[0.16, 12, 12]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.4} metalness={0.8} roughness={0.2} />
      </mesh>
    </group>
  );
}

function RookMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  return (
    <group>
      <mesh position={[0, 0.12, 0]} castShadow>
        <cylinderGeometry args={[0.3, 0.33, 0.16, 16]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.2} metalness={0.9} roughness={0.1} />
      </mesh>
      <mesh position={[0, 0.33, 0]} castShadow>
        <cylinderGeometry args={[0.22, 0.25, 0.3, 12]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.2} metalness={0.9} roughness={0.1} />
      </mesh>
      <mesh position={[0, 0.55, 0]} castShadow>
        <cylinderGeometry args={[0.28, 0.22, 0.18, 12]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.3} metalness={0.9} roughness={0.1} />
      </mesh>
      {/* Battlements */}
      {[-0.16, 0, 0.16].map((offset, i) => (
        <mesh key={i} position={[offset, 0.7, 0]} castShadow>
          <boxGeometry args={[0.1, 0.14, 0.28]} />
          <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.4} metalness={0.9} roughness={0.1} />
        </mesh>
      ))}
    </group>
  );
}

function KnightMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  const mat = <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.3} metalness={0.85} roughness={0.15} />;
  return (
    <group>
      <mesh position={[0, 0.12, 0]} castShadow>
        <cylinderGeometry args={[0.3, 0.33, 0.16, 16]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.31, 0]} castShadow>
        <cylinderGeometry args={[0.2, 0.25, 0.26, 12]} />
        {mat}
      </mesh>
      {/* Body */}
      <mesh position={[0, 0.52, 0.05]} castShadow>
        <boxGeometry args={[0.26, 0.28, 0.3]} />
        {mat}
      </mesh>
      {/* Neck */}
      <mesh position={[0, 0.72, 0.08]} rotation={[0.4, 0, 0]} castShadow>
        <cylinderGeometry args={[0.13, 0.16, 0.2, 10]} />
        {mat}
      </mesh>
      {/* Head */}
      <mesh position={[0, 0.87, 0.15]} castShadow>
        <boxGeometry args={[0.22, 0.18, 0.24]} />
        {mat}
      </mesh>
      {/* Snout */}
      <mesh position={[0, 0.82, 0.28]} castShadow>
        <boxGeometry args={[0.14, 0.1, 0.1]} />
        {mat}
      </mesh>
    </group>
  );
}

function BishopMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  const mat = <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.3} metalness={0.85} roughness={0.15} />;
  return (
    <group>
      <mesh position={[0, 0.12, 0]} castShadow>
        <cylinderGeometry args={[0.29, 0.33, 0.16, 16]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.28, 0]} castShadow>
        <cylinderGeometry args={[0.16, 0.24, 0.22, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.53, 0]} castShadow>
        <cylinderGeometry args={[0.11, 0.16, 0.34, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.78, 0]} castShadow>
        <sphereGeometry args={[0.13, 12, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.96, 0]} castShadow>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={1.0} metalness={0.9} roughness={0.1} />
      </mesh>
    </group>
  );
}

function QueenMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  const mat = <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.4} metalness={0.9} roughness={0.1} />;
  return (
    <group>
      <mesh position={[0, 0.12, 0]} castShadow>
        <cylinderGeometry args={[0.3, 0.34, 0.16, 16]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.3, 0]} castShadow>
        <cylinderGeometry args={[0.18, 0.26, 0.24, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.55, 0]} castShadow>
        <cylinderGeometry args={[0.22, 0.18, 0.3, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.77, 0]} castShadow>
        <cylinderGeometry args={[0.14, 0.22, 0.12, 12]} />
        {mat}
      </mesh>
      {/* Crown points */}
      {[0, 1, 2, 3, 4].map((i) => {
        const angle = (i / 5) * Math.PI * 2;
        return (
          <mesh key={i} position={[Math.sin(angle) * 0.14, 0.9, Math.cos(angle) * 0.14]} castShadow>
            <sphereGeometry args={[0.055, 8, 8]} />
            <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={1.2} metalness={0.9} roughness={0.1} />
          </mesh>
        );
      })}
    </group>
  );
}

function KingMesh({ color }: { color: "w" | "b" }) {
  const c = color === "w" ? "#00aacc" : "#aa00aa";
  const emissive = color === "w" ? "#00f3ff" : "#ff00ff";
  const mat = <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={0.5} metalness={0.9} roughness={0.1} />;
  return (
    <group>
      <mesh position={[0, 0.12, 0]} castShadow>
        <cylinderGeometry args={[0.31, 0.35, 0.16, 16]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.3, 0]} castShadow>
        <cylinderGeometry args={[0.18, 0.27, 0.25, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.56, 0]} castShadow>
        <cylinderGeometry args={[0.24, 0.18, 0.35, 12]} />
        {mat}
      </mesh>
      <mesh position={[0, 0.8, 0]} castShadow>
        <cylinderGeometry args={[0.14, 0.24, 0.1, 12]} />
        {mat}
      </mesh>
      {/* Cross vertical */}
      <mesh position={[0, 1.0, 0]} castShadow>
        <boxGeometry args={[0.07, 0.28, 0.07]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={1.5} metalness={0.9} roughness={0.1} />
      </mesh>
      {/* Cross horizontal */}
      <mesh position={[0, 1.07, 0]} castShadow>
        <boxGeometry args={[0.24, 0.07, 0.07]} />
        <meshStandardMaterial color={c} emissive={emissive} emissiveIntensity={1.5} metalness={0.9} roughness={0.1} />
      </mesh>
    </group>
  );
}

function ChessPiece({
  square,
  type,
  color,
  isSelected,
  isLastMove,
  onClick,
}: {
  square: string;
  type: string;
  color: "w" | "b";
  isSelected: boolean;
  isLastMove: boolean;
  onClick: () => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [x, z] = squareToXZ(square);
  const targetPos = useMemo(() => new THREE.Vector3(x, 0, z), [x, z]);
  const currentPos = useRef(new THREE.Vector3(x, 0, z));
  const velocity = useRef(new THREE.Vector3());
  const prevSquare = useRef(square);
  const [jumping, setJumping] = useState(false);
  const jumpStart = useRef(0);

  useEffect(() => {
    if (prevSquare.current !== square) {
      setJumping(true);
      prevSquare.current = square;
    }
  }, [square]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;

    const target = new THREE.Vector3(x, 0, z);
    const force = target.clone().sub(currentPos.current).multiplyScalar(18);
    velocity.current.add(force.clone().multiplyScalar(delta)).multiplyScalar(0.8);
    currentPos.current.add(velocity.current.clone().multiplyScalar(delta));

    groupRef.current.position.x = currentPos.current.x;
    groupRef.current.position.z = currentPos.current.z;

    // Jump arc animation
    if (jumping) {
      if (jumpStart.current === 0) jumpStart.current = state.clock.elapsedTime;
      const elapsed = state.clock.elapsedTime - jumpStart.current;
      const duration = 0.45;
      if (elapsed < duration) {
        const t = elapsed / duration;
        groupRef.current.position.y = Math.sin(t * Math.PI) * 1.2;
      } else {
        groupRef.current.position.y = 0;
        jumpStart.current = 0;
        setJumping(false);
      }
    } else {
      const hover = Math.sin(state.clock.elapsedTime * 2 + x + z) * 0.03;
      groupRef.current.position.y = hover + (isSelected ? 0.35 : 0);
    }

    // Glow pulse
    if (glowRef.current) {
      const pulse = (Math.sin(state.clock.elapsedTime * 4) + 1) / 2;
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = isSelected
        ? 0.5 + pulse * 0.4
        : 0.15 + pulse * 0.1;
    }
  });

  const glowColor = color === "w" ? "#00f3ff" : "#ff00ff";

  return (
    <group ref={groupRef} position={[x, 0, z]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      {/* Glow base ring */}
      <mesh ref={glowRef} position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.28, 0.42, 32]} />
        <meshBasicMaterial color={glowColor} transparent opacity={0.2} side={THREE.DoubleSide} />
      </mesh>

      {/* Selection indicator */}
      {isSelected && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <circleGeometry args={[0.44, 32]} />
          <meshBasicMaterial color={glowColor} transparent opacity={0.25} />
        </mesh>
      )}

      {/* Last move indicator */}
      {isLastMove && !isSelected && (
        <mesh position={[0, 0.015, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.3, 0.44, 32]} />
          <meshBasicMaterial color="#ffcc00" transparent opacity={0.4} />
        </mesh>
      )}

      {/* Chess piece model */}
      {type === "p" && <PawnMesh color={color} />}
      {type === "r" && <RookMesh color={color} />}
      {type === "n" && <KnightMesh color={color} />}
      {type === "b" && <BishopMesh color={color} />}
      {type === "q" && <QueenMesh color={color} />}
      {type === "k" && <KingMesh color={color} />}
    </group>
  );
}

function BoardTile({
  row,
  col,
  isLight,
  isValidTarget,
  isLastMove,
  isInCheck,
  onClick,
}: {
  row: number;
  col: number;
  isLight: boolean;
  isValidTarget: boolean;
  isLastMove: boolean;
  isInCheck: boolean;
  onClick: () => void;
}) {
  const x = (col - 3.5) * TILE_SIZE;
  const z = (row - 3.5) * TILE_SIZE;
  const glowRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (glowRef.current && isValidTarget) {
      const pulse = (Math.sin(state.clock.elapsedTime * 5) + 1) / 2;
      (glowRef.current.material as THREE.MeshBasicMaterial).opacity = 0.15 + pulse * 0.25;
    }
  });

  const tileColor = isLight ? "#1a1a2e" : "#0a0a1a";

  return (
    <group position={[x, 0, z]} onClick={(e) => { e.stopPropagation(); onClick(); }}>
      {/* Main tile */}
      <mesh receiveShadow>
        <boxGeometry args={[TILE_SIZE, 0.08, TILE_SIZE]} />
        <meshStandardMaterial color={tileColor} roughness={0.1} metalness={0.9} />
      </mesh>

      {/* Subtle cyan grid lines */}
      <mesh position={[0, 0.041, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[TILE_SIZE * 0.98, TILE_SIZE * 0.98]} />
        <meshBasicMaterial color="#00f3ff" wireframe transparent opacity={isLight ? 0.04 : 0.07} />
      </mesh>

      {/* Valid move indicator */}
      {isValidTarget && (
        <>
          <mesh ref={glowRef} position={[0, 0.044, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <circleGeometry args={[0.2, 32]} />
            <meshBasicMaterial color="#4ade80" transparent opacity={0.6} />
          </mesh>
          <mesh position={[0, 0.043, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[TILE_SIZE * 0.9, TILE_SIZE * 0.9]} />
            <meshBasicMaterial color="#4ade80" transparent opacity={0.1} />
          </mesh>
        </>
      )}

      {/* Last move highlight */}
      {isLastMove && (
        <mesh position={[0, 0.042, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[TILE_SIZE * 0.96, TILE_SIZE * 0.96]} />
          <meshBasicMaterial color="#ffcc00" transparent opacity={0.2} />
        </mesh>
      )}

      {/* Check highlight */}
      {isInCheck && (
        <mesh position={[0, 0.042, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[TILE_SIZE * 0.96, TILE_SIZE * 0.96]} />
          <meshBasicMaterial color="#ff0000" transparent opacity={0.35} />
        </mesh>
      )}
    </group>
  );
}

function BoardLabels() {
  return (
    <>
      {FILES.map((file, i) => (
        <group key={`file-${file}`}>
          <mesh position={[(i - 3.5) * TILE_SIZE, 0.05, 4.2]}>
            <planeGeometry args={[0.5, 0.3]} />
            <meshBasicMaterial transparent opacity={0} />
          </mesh>
        </group>
      ))}
    </>
  );
}

function Scene({
  gameState,
  onSquareClick,
}: {
  gameState: ChessGameState;
  onSquareClick: (square: string) => void;
}) {
  const chess = useMemo(() => {
    const c = new Chess();
    try { c.load(gameState.fen); } catch {}
    return c;
  }, [gameState.fen]);

  const pieces = useMemo(() => {
    const board = chess.board();
    const result: Array<{ square: string; type: string; color: "w" | "b" }> = [];
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const piece = board[r][c];
        if (piece) {
          result.push({ square: FILES[c] + RANKS[r], type: piece.type, color: piece.color as "w" | "b" });
        }
      }
    }
    return result;
  }, [gameState.fen]);

  // Find king in check position
  const kingInCheckSquare = useMemo(() => {
    if (!gameState.isCheck) return null;
    const board = chess.board();
    const turn = chess.turn();
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        const p = board[r][c];
        if (p && p.type === "k" && p.color === turn) {
          return FILES[c] + RANKS[r];
        }
      }
    }
    return null;
  }, [gameState.isCheck, gameState.fen]);

  const lastMoveSquares = gameState.lastMove
    ? [gameState.lastMove.from, gameState.lastMove.to]
    : [];

  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 6, 7]} fov={42} />
      <OrbitControls enablePan={false} maxPolarAngle={Math.PI / 2.2} minDistance={5} maxDistance={14} />

      <ambientLight intensity={0.4} />
      <pointLight position={[0, 8, 0]} intensity={1.5} castShadow color="#00f3ff" />
      <spotLight position={[-6, 8, -6]} angle={0.3} penumbra={0.8} intensity={0.8} castShadow color="#ff00ff" />
      <spotLight position={[6, 8, 6]} angle={0.3} penumbra={0.8} intensity={0.8} castShadow color="#00f3ff" />

      <group>
        {/* Board base */}
        <mesh receiveShadow position={[0, -0.08, 0]}>
          <boxGeometry args={[8.5, 0.12, 8.5]} />
          <meshStandardMaterial color="#020210" metalness={1} roughness={0.05} />
        </mesh>

        {/* Glowing border frame */}
        {[
          [0, 0.01, 4.3, 8.6, 0.05, 0.1],
          [0, 0.01, -4.3, 8.6, 0.05, 0.1],
          [4.3, 0.01, 0, 0.1, 0.05, 8.6],
          [-4.3, 0.01, 0, 0.1, 0.05, 8.6],
        ].map(([x, y, z, w, h, d], i) => (
          <mesh key={i} position={[x as number, y as number, z as number]}>
            <boxGeometry args={[w as number, h as number, d as number]} />
            <meshBasicMaterial color={i % 2 === 0 ? "#00f3ff" : "#ff00ff"} />
          </mesh>
        ))}

        {/* Tiles */}
        {Array.from({ length: 8 }).map((_, row) =>
          Array.from({ length: 8 }).map((_, col) => {
            const square = FILES[col] + RANKS[row];
            const isLight = (row + col) % 2 === 0;
            return (
              <BoardTile
                key={square}
                row={row}
                col={col}
                isLight={isLight}
                isValidTarget={gameState.validMoveSquares.includes(square)}
                isLastMove={lastMoveSquares.includes(square)}
                isInCheck={square === kingInCheckSquare}
                onClick={() => onSquareClick(square)}
              />
            );
          })
        )}

        {/* Pieces */}
        {pieces.map(({ square, type, color }) => (
          <ChessPiece
            key={`${square}-${type}-${color}`}
            square={square}
            type={type}
            color={color}
            isSelected={gameState.selectedSquare === square}
            isLastMove={lastMoveSquares.includes(square)}
            onClick={() => onSquareClick(square)}
          />
        ))}

        <ContactShadows position={[0, -0.04, 0]} opacity={0.5} scale={12} blur={2} far={1} />
      </group>

      <Environment preset="city" />
    </>
  );
}

export function Board({ gameState, onSquareClick }: BoardProps) {
  return (
    <div
      data-testid="chess-board"
      className="w-full aspect-[16/10] md:aspect-[21/9] min-h-[420px] rounded-xl overflow-hidden border border-primary/30 bg-black/60 relative shadow-[0_0_60px_rgba(0,243,255,0.12)]"
    >
      <Canvas shadows dpr={[1, 2]}>
        <Scene gameState={gameState} onSquareClick={onSquareClick} />
      </Canvas>

      <div className="absolute bottom-3 left-4 right-4 pointer-events-none flex justify-between items-end opacity-30">
        <div className="text-[9px] font-mono text-primary uppercase tracking-widest">
          Drag to orbit · Scroll to zoom
        </div>
        <div className="text-[9px] font-mono text-secondary uppercase tracking-widest">
          {gameState.isCheck ? "⚡ CHECK" : ""}
        </div>
      </div>
    </div>
  );
}
