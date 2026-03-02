import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { useCursor, Text, Cylinder, Box, Sphere, Cone, Torus } from '@react-three/drei';
import * as THREE from 'three';

interface Board3DProps {
  game: any;
  onMove: (source: string, target: string) => void;
  orientation: 'white' | 'black';
}

export function Board3D({ game, onMove, orientation }: Board3DProps) {
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [hoveredSquare, setHoveredSquare] = useState<string | null>(null);
  
  const board = useMemo(() => {
    const squares = [];
    for (let i = 0; i < 8; i++) {
      for (let j = 0; j < 8; j++) {
        const file = String.fromCharCode(97 + j);
        const rank = (8 - i).toString();
        const square = file + rank;
        const isDark = (i + j) % 2 === 1;
        squares.push({ square, i, j, isDark });
      }
    }
    return squares;
  }, []);

  const pieces = useMemo(() => {
    const result = [];
    const boardState = game.board();
    for (let i = 0; i < 8; i++) {
      for (let j = 0; j < 8; j++) {
        const piece = boardState[i][j];
        if (piece) {
          const file = String.fromCharCode(97 + j);
          const rank = (8 - i).toString();
          result.push({ 
            type: piece.type, 
            color: piece.color, 
            square: file + rank,
            i, j 
          });
        }
      }
    }
    return result;
  }, [game]);

  const handleSquareClick = (square: string) => {
    if (selectedSquare === square) {
      setSelectedSquare(null);
    } else if (selectedSquare) {
      onMove(selectedSquare, square);
      setSelectedSquare(null);
    } else {
      const piece = game.get(square);
      if (piece && piece.color === game.turn()) {
        setSelectedSquare(square);
      }
    }
  };

  return (
    <group rotation={[-Math.PI / 2.5, 0, 0]}>
      {/* Board Base */}
      <mesh position={[3.5, 3.5, -0.15]}>
        <boxGeometry args={[8.5, 8.5, 0.2]} />
        <meshStandardMaterial color="#020202" metalness={0.9} roughness={0.1} />
      </mesh>

      {/* Squares */}
      {board.map(({ square, i, j, isDark }) => (
        <Square
          key={square}
          position={[j, 7 - i, 0]}
          isDark={isDark}
          isSelected={selectedSquare === square}
          isHovered={hoveredSquare === square}
          onClick={() => handleSquareClick(square)}
          onPointerOver={() => setHoveredSquare(square)}
          onPointerOut={() => setHoveredSquare(null)}
        />
      ))}

      {/* Pieces */}
      {pieces.map((piece, idx) => (
        <Piece
          key={`${piece.square}-${idx}`}
          type={piece.type}
          color={piece.color}
          position={[piece.j, 7 - piece.i, 0.1]}
          isSelected={selectedSquare === piece.square}
        />
      ))}

      <ambientLight intensity={1.5} />
      <pointLight position={[4, 4, 8]} intensity={3} color="#00f3ff" />
      <pointLight position={[-4, -4, 8]} intensity={3} color="#ff00a0" />
      <directionalLight position={[0, 0, 10]} intensity={1.5} />
    </group>
  );
}

function Square({ position, isDark, isSelected, isHovered, onClick, onPointerOver, onPointerOut }: any) {
  useCursor(isHovered);
  const color = isSelected ? '#fdff00' : isHovered ? '#00f3ff' : isDark ? '#0a0a0a' : '#444444';
  const glowIntensity = isSelected || isHovered ? 2 : (isDark ? 0.1 : 0.3);
  const borderEmissive = isDark ? '#00f3ff' : '#ff00a0';

  return (
    <group position={position}>
      <mesh 
        onClick={(e) => { e.stopPropagation(); onClick(); }}
        onPointerOver={(e) => { e.stopPropagation(); onPointerOver(); }}
        onPointerOut={onPointerOut}
      >
        <planeGeometry args={[0.98, 0.98]} />
        <meshStandardMaterial 
          color={color} 
          emissive={color}
          emissiveIntensity={glowIntensity * 0.5}
          metalness={0.7}
          roughness={0.2}
        />
      </mesh>
      <mesh position={[0, 0, 0.005]}>
        <ringGeometry args={[0.47, 0.49, 4]} rotation={[0, 0, Math.PI / 4]} />
        <meshStandardMaterial 
          color={borderEmissive} 
          emissive={borderEmissive} 
          emissiveIntensity={0.5} 
          transparent 
          opacity={0.3} 
        />
      </mesh>
    </group>
  );
}

function Piece({ type, color, position, isSelected }: any) {
  const groupRef = useRef<THREE.Group>(null);
  const baseColor = color === 'w' ? '#00f3ff' : '#ff00a0';
  const [zOffset, setZOffset] = useState(0.1);
  
  useFrame((state) => {
    if (isSelected) {
      const targetZ = 0.5 + Math.sin(state.clock.getElapsedTime() * 5) * 0.1;
      setZOffset(targetZ);
      if (groupRef.current) {
        groupRef.current.rotation.z += 0.02;
      }
    } else {
      setZOffset(0.1);
    }
  });

  return (
    <group position={[position[0], position[1], zOffset]} ref={groupRef}>
      <ClassicCyborgPiece type={type} color={baseColor} isSelected={isSelected} />
    </group>
  );
}

function ClassicCyborgPiece({ type, color, isSelected }: any) {
  const glowIntensity = isSelected ? 2 : 0.8;
  const matProps = {
    color: color,
    emissive: color,
    emissiveIntensity: glowIntensity * 0.4,
    metalness: 0.8,
    roughness: 0.2,
    transparent: true,
    opacity: 0.9
  };

  // Base for all pieces
  const Base = () => (
    <Cylinder args={[0.35, 0.4, 0.15, 16]} position={[0, 0, 0.075]}>
      <meshStandardMaterial {...matProps} />
    </Cylinder>
  );

  switch (type) {
    case 'p': // Pawn
      return (
        <group>
          <Base />
          <Cylinder args={[0.15, 0.25, 0.4, 16]} position={[0, 0, 0.3]} rotation={[Math.PI / 2, 0, 0]}>
             <meshStandardMaterial {...matProps} />
          </Cylinder>
          <Sphere args={[0.18, 16, 16]} position={[0, 0, 0.6]}>
            <meshStandardMaterial {...matProps} />
          </Sphere>
        </group>
      );
    case 'r': // Rook
      return (
        <group>
          <Base />
          <Cylinder args={[0.28, 0.3, 0.6, 16]} position={[0, 0, 0.4]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
          <Cylinder args={[0.32, 0.32, 0.2, 8]} position={[0, 0, 0.8]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
        </group>
      );
    case 'n': // Knight
      return (
        <group>
          <Base />
          <Cylinder args={[0.2, 0.3, 0.5, 16]} position={[0, 0, 0.3]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
          <group position={[0, 0.1, 0.65]} rotation={[Math.PI / 6, 0, 0]}>
            <Box args={[0.2, 0.4, 0.3]}>
              <meshStandardMaterial {...matProps} />
            </Box>
            <Cone args={[0.1, 0.25, 4]} position={[0, 0.15, 0.1]} rotation={[Math.PI, 0, 0]}>
              <meshStandardMaterial {...matProps} />
            </Cone>
          </group>
        </group>
      );
    case 'b': // Bishop
      return (
        <group>
          <Base />
          <Cylinder args={[0.12, 0.25, 0.7, 16]} position={[0, 0, 0.45]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
          <Sphere args={[0.18, 16, 16]} position={[0, 0, 0.85]} scale={[0.8, 0.8, 1.2]}>
            <meshStandardMaterial {...matProps} />
          </Sphere>
          <Torus args={[0.15, 0.02, 8, 16]} position={[0, 0, 0.9]} rotation={[Math.PI / 2, 0, 0]}>
             <meshStandardMaterial {...matProps} />
          </Torus>
        </group>
      );
    case 'q': // Queen
      return (
        <group>
          <Base />
          <Cylinder args={[0.15, 0.3, 0.9, 16]} position={[0, 0, 0.55]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
          <Sphere args={[0.25, 16, 16]} position={[0, 0, 1.05]} scale={[1.1, 1.1, 0.8]}>
            <meshStandardMaterial {...matProps} />
          </Sphere>
          <Torus args={[0.28, 0.04, 8, 24]} position={[0, 0, 1.05]} rotation={[Math.PI / 2, 0, 0]}>
             <meshStandardMaterial {...matProps} />
          </Torus>
          <Sphere args={[0.08, 8, 8]} position={[0, 0, 1.25]}>
            <meshStandardMaterial {...matProps} />
          </Sphere>
        </group>
      );
    case 'k': // King
      return (
        <group>
          <Base />
          <Cylinder args={[0.18, 0.3, 1.0, 16]} position={[0, 0, 0.6]} rotation={[Math.PI / 2, 0, 0]}>
            <meshStandardMaterial {...matProps} />
          </Cylinder>
          <Box args={[0.4, 0.4, 0.3]} position={[0, 0, 1.1]}>
            <meshStandardMaterial {...matProps} />
          </Box>
          <Box args={[0.12, 0.12, 0.4]} position={[0, 0, 1.4]}>
            <meshStandardMaterial {...matProps} />
          </Box>
          <Box args={[0.3, 0.12, 0.12]} position={[0, 0, 1.45]}>
            <meshStandardMaterial {...matProps} />
          </Box>
        </group>
      );
    default:
      return null;
  }
}
