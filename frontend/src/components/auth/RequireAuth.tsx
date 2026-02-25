"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getUser } from "@/utils/storage";
import { useAuthStore } from "@/store/auth.store";

type RequireAuthProps = {
  children: React.ReactNode;
};

export default function RequireAuth({ children }: RequireAuthProps) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const setAuthenticated = useAuthStore((state) => state.setAuthenticated);

  useEffect(() => {
    // Los tokens están en cookies httpOnly
    // Verificamos si hay datos de usuario guardados
    const user = getUser();

    if (!user) {
      // Si no hay usuario, redirigir al login
      router.replace("/login");
      return;
    }

    // Restaurar estado de autenticación
    setAuthenticated(true, user);
  }, [router, setAuthenticated]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
