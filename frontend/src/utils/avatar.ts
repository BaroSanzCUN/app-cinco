// src/utils/avatar.ts
/**
 * Utilidades para manejar avatares de empleados
 */

const AVATAR_BASE_URL = "https://www.cincosas.com/2mp21d4s/photos/";
const AVATAR_ALT_BASE_URL = "https://cinco.net.co/perfil/photos/";
const DEFAULT_AVATAR = "/images/user/owner.png";

/**
 * Obtiene la URL completa del avatar del empleado
 * @param linkFoto - Path o URL completa de la foto
 * @returns URL válida del avatar
 */
export const getAvatarUrl = (linkFoto?: string | null): string => {
  if (!linkFoto || linkFoto.trim() === "") {
    return DEFAULT_AVATAR;
  }

  // Si ya es una URL completa válida, devolverla tal cual
  try {
    const url = new URL(linkFoto);
    return linkFoto;
  } catch {
    // No es una URL completa, procesar el path
  }

  // Limpiar el path de navegación relativa (..)
  let cleanPath = linkFoto.trim();
  
  // Si contiene referencias al dominio alternativo cinco.net.co
  if (cleanPath.includes("cinco.net.co/perfil/photos/")) {
    // Extraer solo el nombre del archivo
    const match = cleanPath.match(/cinco\.net\.co\/perfil\/photos\/(.+)$/);
    if (match && match[1]) {
      return `${AVATAR_ALT_BASE_URL}${match[1]}`;
    }
  }
  
  // Si contiene ../ al inicio, removerlo
  cleanPath = cleanPath.replace(/^(\.\.\/)+/, "");
  
  // Si el path ya comienza con "photos/", usar solo la base del dominio
  if (cleanPath.startsWith("photos/")) {
    return `https://www.cincosas.com/2mp21d4s/${cleanPath}`;
  }
  
  // Construir la URL con la base principal
  return `${AVATAR_BASE_URL}${cleanPath}`;
};

/**
 * Precargar imágenes de avatares en el navegador
 * @param imageUrls - Array de URLs de imágenes para precargar
 */
export const preloadAvatars = (imageUrls: string[]): void => {
  if (typeof window === "undefined") return;

  imageUrls.forEach((url) => {
    const img = new Image();
    img.src = url;
  });
};

/**
 * Precargar avatar de un empleado específico
 * @param linkFoto - Path o URL de la foto
 */
export const preloadAvatar = (linkFoto?: string | null): void => {
  if (!linkFoto) return;
  
  const url = getAvatarUrl(linkFoto);
  const img = new Image();
  img.src = url;
};
