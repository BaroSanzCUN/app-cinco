import { Metadata } from "next";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";

export const metadata: Metadata = {
  title: "Index - CINCO SAS",
  description: "Bienvenido a la página principal de CINCO SAS.",
};

const HomePage = () => {
  return (
    <div>
      <PageBreadcrumb pageTitle="Inicio" />
      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-5 py-7 dark:border-gray-800 dark:bg-white/3 xl:px-10 xl:py-12">
        <div className="mx-auto w-full max-w-157.5 text-center">
          <h3 className="mb-4 font-semibold text-gray-800 text-theme-xl dark:text-white/90 sm:text-2xl">
            Bienvenido a CINCO SAS
          </h3>

          <p className="text-sm text-gray-500 dark:text-gray-400 sm:text-base">
            Explora tu panel de control y gestiona tus operaciones de manera eficiente.
          </p>

        </div>
      </div>
    </div>
  )
}
export default HomePage;