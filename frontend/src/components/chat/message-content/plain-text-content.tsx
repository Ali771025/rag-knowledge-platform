interface PlainTextContentProps {
  text: string;
}

export function PlainTextContent({ text }: PlainTextContentProps) {
  return <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{text}</p>;
}
