/** HTML5 drag payload for comparing simulation runs. */
export const RUN_DRAG_MIME = 'application/x-sim-run-id';

export function setRunDragData(dataTransfer: DataTransfer, runId: string) {
  dataTransfer.setData(RUN_DRAG_MIME, runId);
  dataTransfer.setData('text/plain', runId);
  dataTransfer.effectAllowed = 'copy';
}

export function readRunDragId(dataTransfer: DataTransfer): string | null {
  const typed = dataTransfer.getData(RUN_DRAG_MIME);
  if (typed) return typed;
  const plain = dataTransfer.getData('text/plain');
  return plain || null;
}

export function isRunDrag(dataTransfer: DataTransfer): boolean {
  return (
    dataTransfer.types.includes(RUN_DRAG_MIME) ||
    dataTransfer.types.includes('text/plain')
  );
}
