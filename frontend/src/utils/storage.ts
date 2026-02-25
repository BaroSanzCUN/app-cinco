// src/utils/storage.ts
// Los tokens ahora se manejan en cookies httpOnly por seguridad
// Solo gestionamos datos del usuario en localStorage

const getUser = () => {
    try {
        const userStr = localStorage.getItem("user");
        return userStr ? JSON.parse(userStr) : null;
    } catch {
        return null;
    }
}

const saveUser = (user: any) => {
    if (user) {
        localStorage.setItem("user", JSON.stringify(user));
    }
}

const clearUser = () => {
    localStorage.removeItem("user");
}

export { getUser, saveUser, clearUser };