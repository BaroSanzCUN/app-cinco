// app/hooks/useFormSubmit.ts
import api from "@/lib/api";
import { useState } from "react";
import { classifyError, ApiErrorDetail } from "@/lib/errorHandler";

type SubmitOptions<T> = {
  endpoint: string;
  method?: "POST" | "PUT" | "PATCH";
  onSuccess?: (data: any) => void;
  onError?: (error: ApiErrorDetail) => void;
};

export function useFormSubmit<T>() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
  const [data, setData] = useState<any>(null);

  const submit = async (formData: T, options: SubmitOptions<T>) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api({
        url: options.endpoint,
        method: options.method || "POST",
        data: formData,
      });

      setData(response.data);
      options.onSuccess?.(response.data);
      return response.data;
    } catch (err: any) {
      // Normalize error shape for UI and logs
      const errorDetail: ApiErrorDetail = classifyError(err);

      setError(errorDetail);
      options.onError?.(errorDetail);

      throw errorDetail;
    } finally {
      setIsLoading(false);
    }
  };

  return { submit, isLoading, error, data };
}
