// src/utils/storage.ts
// Los tokens ahora se manejan en cookies httpOnly por seguridad
// Solo gestionamos datos del usuario en sessionStorage (más seguro que localStorage)

const getUser = () => {
  try {
    const userStr = sessionStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : null;
  } catch {
    return null;
  }
};

const saveUser = (user: any) => {
  if (user) {
    sessionStorage.setItem("user", JSON.stringify(user));
  }
};

const clearUser = () => {
  sessionStorage.removeItem("user");
};

export { getUser, saveUser, clearUser };
