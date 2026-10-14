import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { memo } from "react";
import clsx from "clsx";

interface Props {
  content: string;
  className?: string;
}

/**
 * Renders lesson markdown with the `.md-body` typographic styles defined in index.css.
 */
export const Markdown = memo(function Markdown({ content, className }: Props) {
  return (
    <div className={clsx("md-body", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
});
