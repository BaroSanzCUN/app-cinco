"use client";

import { ArrowDown } from "lucide-react";

type ScrollToBottomButtonProps = {
  onClick: () => void;
  unreadCount: number;
};

const ScrollToBottomButton = ({
  onClick,
  unreadCount,
}: ScrollToBottomButtonProps) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="border-brand-200 text-brand-700 shadow-theme-md hover:bg-brand-50 dark:border-brand-700 dark:text-brand-300 absolute right-4 bottom-4 z-20 inline-flex items-center gap-2 rounded-full border bg-white px-3 py-2 text-xs font-semibold transition dark:bg-gray-900 dark:hover:bg-gray-800"
      title="Ir al final"
    >
      <ArrowDown size={14} />
      <span>Ir al final</span>
      {unreadCount > 0 && (
        <span className="bg-brand-500 rounded-full px-1.5 py-0.5 text-[10px] text-white">
          {unreadCount}
        </span>
      )}
    </button>
  );
};

export default ScrollToBottomButton;
