import { ReactNode } from "react";
import { FieldValues, UseFormHandleSubmit } from "react-hook-form";

interface FormProps<T extends FieldValues> {
  children: ReactNode;
  handleSubmit: UseFormHandleSubmit<T>;
  onSubmit: (data: T) => void;
  className?: string;
}

const Form = <T extends FieldValues>({
  children,
  handleSubmit,
  onSubmit,
  className,
}: FormProps<T>) => {
  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className={className}
      noValidate
    >
      {children}
    </form>
  );
};

export default Form;
