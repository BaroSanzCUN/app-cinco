"use client";
import { useState } from "react";
import Form from "@/components/form/Form";
import Label from "@/components/form/Label";
import { useRouter } from "next/navigation";
import { EyeCloseIcon, EyeIcon } from "@/icons";
import { useAuthStore } from "@/store/auth.store";
import Button from "@/components/ui/button/Button";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import Input from "@/components/form/input/InputField";
import { getErrorMessage, ApiErrorType } from "@/lib/errorHandler";
import { loginSchema, LoginFormValues } from "@/schemas/auth.schema";

export default function SignInForm() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const [showPassword, setShowPassword] = useState(false);
  const { submit, isLoading, error } = useFormSubmit<LoginFormValues>();
  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const onSubmit = async (data: LoginFormValues) => {
    try {
      await submit(data, {
        endpoint: "/auth/login",
        onSuccess: (response) => {
          login(response);
          router.replace("/");
        },
        onError: (error) => {
          console.error("Error al iniciar sesión:", {
            type: error.type,
            status: error.status,
            message: error.message,
            detail: error.detail,
            errors: error.errors
          });
        },
      });
    } catch (error) {
      // El error ya fue manejado por useFormSubmit
      // Solo lo capturamos aquí para prevenir errores no capturados
    }
  };

  const handleForgotPassword = () => {
    // router.push("/forgot-password");
    alert("Para reestablecer tu contraseña, por favor contacta a tu lider.");
  }

  return (
    <div className="flex flex-col flex-1 lg:w-1/2 w-full">
      <div className="flex flex-col justify-center flex-1 w-full max-w-md mx-auto">
        <div>
          <div className="mb-5 sm:mb-8">
            <h1 className="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md">
              Bienvenido de nuevo
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Ingresa tus credenciales para acceder a tu cuenta.
            </p>
          </div>
          <div>
            <div className="relative py-3 sm:py-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200 dark:border-gray-800"></div>
              </div>
            </div>
            <Form handleSubmit={handleSubmit} onSubmit={onSubmit}>
              <div className="space-y-6">
                <div>
                  <Label htmlFor="username">
                    Nombre de usuario <span className="text-error-400">*</span>{" "}
                  </Label>
                  <Controller
                    control={control}
                    name="username"
                    render={({ field }) => (
                      <Input
                        {...field}
                        id="username"
                        type="text"
                        inputMode="text"
                        autoComplete="username"
                        placeholder="Ingresa tu nombre de usuario"
                        error={Boolean(errors.username)}
                        hint={errors.username?.message}
                      />
                    )}
                  />
                </div>
                <div>
                  <Label htmlFor="password">
                    Contraseña <span className="text-error-400">*</span>{" "}
                  </Label>
                  <div className="relative">
                    <Controller
                      control={control}
                      name="password"
                      render={({ field }) => (
                        <Input
                          {...field}
                          id="password"
                          type={showPassword ? "text" : "password"}
                          autoComplete="current-password"
                          placeholder="Ingresa tu contraseña"
                          error={Boolean(errors.password)}
                          hint={errors.password?.message}
                        />
                      )}
                    />
                    <span
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute z-30 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                    >
                      {showPassword ? (
                        <EyeIcon className="fill-gray-500 dark:fill-gray-400" />
                      ) : (
                        <EyeCloseIcon className="fill-gray-500 dark:fill-gray-400" />
                      )}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-center">
                  <span
                    onClick={() => handleForgotPassword()}
                    className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400 cursor-pointer"
                  >
                    ¿Olvidaste tu contraseña?
                  </span>
                </div>
                <div>
                  <Button
                    size="sm"
                    type="submit"
                    className="w-full"
                    disabled={isSubmitting || isLoading}
                  >
                    Iniciar sesión
                  </Button>
                </div>
              </div>
            </Form>

            <div className="mt-5">
              {error && (
                <div className="space-y-2">
                  <p className="text-sm font-normal text-center text-error-600 dark:text-error-400">
                    {getErrorMessage(error)}
                  </p>
                  {error.type === ApiErrorType.VALIDATION && error.errors && (
                    <ul className="text-xs text-error-500 space-y-1">
                      {Object.entries(error.errors).map(([field, messages]) => (
                        <li key={field}>
                          {Array.isArray(messages) ? messages[0] : messages}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
