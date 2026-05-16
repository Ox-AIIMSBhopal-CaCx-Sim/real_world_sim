import { useCallback, useEffect, useRef } from 'react';

interface ResizeHandleProps {
  onDrag: (deltaX: number) => void;
  ariaLabel: string;
}

export function ResizeHandle({ onDrag, ariaLabel }: ResizeHandleProps) {
  const dragging = useRef(false);
  const lastX = useRef(0);

  const onMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!dragging.current) return;
      const delta = e.clientX - lastX.current;
      lastX.current = e.clientX;
      onDrag(delta);
    },
    [onDrag],
  );

  const onMouseUp = useCallback(() => {
    dragging.current = false;
    document.body.classList.remove('is-resizing');
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
  }, [onMouseMove]);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      lastX.current = e.clientX;
      document.body.classList.add('is-resizing');
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);
    },
    [onMouseMove, onMouseUp],
  );

  useEffect(() => () => onMouseUp(), [onMouseUp]);

  return (
    <div
      className="resize-handle"
      role="separator"
      aria-orientation="vertical"
      aria-label={ariaLabel}
      tabIndex={0}
      onMouseDown={onMouseDown}
    />
  );
}
