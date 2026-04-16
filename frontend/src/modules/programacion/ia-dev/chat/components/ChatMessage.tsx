"use client";

import { memo } from "react";
import type { IADevAction } from "@/services/ia-dev.service";
import type { ChatMessageModel } from "@/modules/programacion/ia-dev/chat/types";
import UserMessage from "@/modules/programacion/ia-dev/chat/components/UserMessage";
import AssistantMessage from "@/modules/programacion/ia-dev/chat/components/AssistantMessage";

type ChatMessageProps = {
  message: ChatMessageModel;
  onActionClick: (action: IADevAction) => void;
  isBusy: boolean;
};

const ChatMessage = ({ message, onActionClick, isBusy }: ChatMessageProps) => {
  if (message.role === "user") {
    return <UserMessage message={message} />;
  }

  return (
    <AssistantMessage
      message={message}
      onActionClick={onActionClick}
      isBusy={isBusy}
    />
  );
};

export default memo(ChatMessage);
