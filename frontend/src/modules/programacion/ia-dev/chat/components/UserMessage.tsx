"use client";

import { memo } from "react";
import type { ChatMessageModel } from "@/modules/programacion/ia-dev/chat/types";

type UserMessageProps = {
  message: ChatMessageModel;
};

const UserMessage = ({ message }: UserMessageProps) => {
  return (
    <article className="bg-brand-500 shadow-theme-sm ml-auto max-w-[95%] rounded-2xl rounded-br-md px-4 py-3 text-sm text-white">
      <p className="whitespace-pre-wrap">{message.content}</p>
    </article>
  );
};

export default memo(UserMessage);
