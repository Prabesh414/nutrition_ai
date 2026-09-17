/**
 * Drag-or-tap behaviour for the floating coach button.
 *
 * Mouse and touch previously had two near-identical effects; both are handled
 * here through Pointer Events, which cover mouse, touch and pen uniformly.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

const EDGE_MARGIN = 10;
const BUTTON_SIZE = 70;
const TAP_THRESHOLD_PX = 5;

export interface Position {
  x: number;
  y: number;
}

function clampToViewport(position: Position): Position {
  const maxX = Math.max(0, window.innerWidth - BUTTON_SIZE);
  const maxY = Math.max(0, window.innerHeight - BUTTON_SIZE);
  return {
    x: Math.min(Math.max(EDGE_MARGIN, position.x), maxX),
    y: Math.min(Math.max(EDGE_MARGIN, position.y), maxY),
  };
}

export function useDraggable(onTap: () => void) {
  const [position, setPosition] = useState<Position>(() =>
    clampToViewport({ x: window.innerWidth - 80, y: window.innerHeight - 85 }),
  );
  const [dragging, setDragging] = useState(false);

  const offset = useRef<Position>({ x: 0, y: 0 });
  const origin = useRef<Position>({ x: 0, y: 0 });
  // Held in a ref so the move/up listeners never need re-binding on each frame.
  const tapHandler = useRef(onTap);
  tapHandler.current = onTap;

  useEffect(() => {
    const handleResize = () => setPosition(clampToViewport);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const onPointerDown = useCallback((event: React.PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0 && event.pointerType === 'mouse') return;
    const rect = event.currentTarget.getBoundingClientRect();
    offset.current = { x: event.clientX - rect.left, y: event.clientY - rect.top };
    origin.current = { x: event.clientX, y: event.clientY };
    setDragging(true);
  }, []);

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (event: PointerEvent) => {
      setPosition(
        clampToViewport({
          x: event.clientX - offset.current.x,
          y: event.clientY - offset.current.y,
        }),
      );
    };

    const handleUp = (event: PointerEvent) => {
      setDragging(false);
      const movedX = Math.abs(event.clientX - origin.current.x);
      const movedY = Math.abs(event.clientY - origin.current.y);
      if (movedX < TAP_THRESHOLD_PX && movedY < TAP_THRESHOLD_PX) tapHandler.current();
    };

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    window.addEventListener('pointercancel', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
      window.removeEventListener('pointercancel', handleUp);
    };
  }, [dragging]);

  return { position, dragging, onPointerDown };
}
