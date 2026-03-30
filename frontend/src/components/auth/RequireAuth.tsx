"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth.store";

type RequireAuthProps = {
  children: React.ReactNode;
};

export default function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isCheckingSession = useAuthStore((state) => state.isCheckingSession);
  const hydrateFromStorage = useAuthStore((state) => state.hydrateFromStorage);
  const validateCurrentSession = useAuthStore(
    (state) => state.validateCurrentSession,
  );
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const bootstrapAuth = async () => {
      hydrateFromStorage();
      const user = await validateCurrentSession();

      if (!isMounted) return;

      if (!user) {
        router.replace("/login");
      }

      setIsReady(true);
    };

    bootstrapAuth();

    return () => {
      isMounted = false;
    };
  }, [hydrateFromStorage, router, validateCurrentSession]);

  if (!isReady || isCheckingSession) {
    return null;
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
