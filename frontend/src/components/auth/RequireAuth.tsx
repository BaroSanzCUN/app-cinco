"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getTokens, getUser } from "@/utils/storage";
import { useAuthStore } from "@/store/auth.store";

type RequireAuthProps = {
  children: React.ReactNode;
};

export default function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

  useEffect(() => {
    const { accessToken } = getTokens();

    if (!accessToken) {
      router.replace("/login");
      return;
    }

    // Restaurar usuario desde localStorage
    const user = getUser();
    setAuthenticated(true, user);
  }, [router, setAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
