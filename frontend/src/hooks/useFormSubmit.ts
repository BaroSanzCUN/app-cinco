// app/hooks/useFormSubmit.ts
import api from '@/lib/api';
import { useState } from 'react';

type SubmitOptions<T> = {
  endpoint: string;
  method?: 'POST' | 'PUT' | 'PATCH';
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
};

export function useFormSubmit<T>() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Record<string, any> | null>(null);
  const [data, setData] = useState<any>(null);

  const submit = async (formData: T, options: SubmitOptions<T>) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api({
        url: options.endpoint,
        method: options.method || 'POST',
        data: formData,
      });

      setData(response.data);

      options.onSuccess?.(response.data);

      return response.data;

    } catch (err: any) {
      const backendErrors = err.response?.data || null;

      setError(backendErrors);

      options.onError?.(backendErrors);

      throw backendErrors;

    } finally {
      setIsLoading(false);
    }
  };

  return { submit, isLoading, error, data };
}
