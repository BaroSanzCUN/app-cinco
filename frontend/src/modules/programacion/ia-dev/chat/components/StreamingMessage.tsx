"use client";

import { Loader2 } from "lucide-react";

const StreamingMessage = () => {
  return (
    <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
      <Loader2 size={12} className="animate-spin" />
      IA escribiendo...
    </div>
  );
};

export default StreamingMessage;
