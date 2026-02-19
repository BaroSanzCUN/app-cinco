// src/utils/storage.ts
const getTokens = () => {
    const accessToken = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");
    return { accessToken, refreshToken };
}

const saveTokens = (data: any) => {
    // Django usa 'access' y 'refresh', algunos backends usan 'access_token' y 'refresh_token'
    const accessToken = data.access || data.access_token;
    const refreshToken = data.refresh || data.refresh_token;
    
    if (accessToken) {
        localStorage.setItem("access_token", accessToken);
    }
    if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
    }

    // Guardar usuario si existe
    if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
    }
}

const clearTokens = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
}

const getUser = () => {
    try {
        const userStr = localStorage.getItem("user");
        return userStr ? JSON.parse(userStr) : null;
    } catch {
        return null;
    }
}

export { getTokens, saveTokens, clearTokens, getUser };