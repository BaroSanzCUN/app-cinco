// src/services/auth.service.ts
import axios from "axios";
import { getTokens, saveTokens } from "@/utils/storage";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/";

export async function refreshToken() {
  const { refreshToken } = getTokens();

  const res = await axios.post(`${baseURL}auth/refresh/`, {
    refresh_token: refreshToken,
  });

  saveTokens(res.data);
  return res.data.access_token;
}
