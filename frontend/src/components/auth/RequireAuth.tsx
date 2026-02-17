"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getTokens } from "@/utils/storage";
import { useAuthStore } from "@/store/auth.store";

type RequireAuthProps = {
  children: React.ReactNode;
};

export default function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const { isAuthenticated, setAuthenticated } = useAuthStore((state) => ({
    isAuthenticated: state.isAuthenticated,
    setAuthenticated: state.setAuthenticated,
  }));

  useEffect(() => {
    const { accessToken } = getTokens();

    if (!accessToken) {
      router.replace("/login");
      return;
    }

    setAuthenticated(true);
  }, [router, setAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
