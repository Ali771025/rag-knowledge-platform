const CONVERSATION_DRAG_MIME = "application/x-ragai-conversation";

export function writeDraggedConversationId(dataTransfer: DataTransfer, conversationId: string) {
  dataTransfer.effectAllowed = "move";
  dataTransfer.setData(CONVERSATION_DRAG_MIME, conversationId);
  dataTransfer.setData("text/plain", conversationId);
}

export function readDraggedConversationId(dataTransfer: DataTransfer): string | null {
  const typed = dataTransfer.getData(CONVERSATION_DRAG_MIME).trim();
  if (typed) {
    return typed;
  }

  const fallback = dataTransfer.getData("text/plain").trim();
  return fallback || null;
}
