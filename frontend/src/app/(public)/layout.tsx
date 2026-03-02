import React from "react";
// import Link from "next/link";
import Image from "next/image";
import GridShape from "@/components/common/GridShape";
import { ThemeProvider } from "@/context/ThemeContext";
import ThemeTogglerTwo from "@/components/common/ThemeTogglerTwo";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative z-1 bg-white p-6 sm:p-0 dark:bg-gray-900">
      <ThemeProvider>
        <div className="relative flex h-screen w-full flex-col justify-center sm:p-0 lg:flex-row dark:bg-gray-900">
          <div className="hidden h-full w-full items-center bg-[#1c2433] lg:grid lg:w-1/2">
            <div className="relative z-1 flex items-center justify-center">
              {/* <!-- ===== Common Grid Shape Start ===== --> */}
              <GridShape />
              <div className="flex max-w-xs flex-col items-center">
                {/* <Link href="/" className="block mb-4"> */}
                <Image
                  width={231}
                  height={48}
                  src="/images/logo/logo-cinco.svg"
                  alt="Logo"
                />
                {/* </Link> */}
              </div>
            </div>
          </div>
          {children}
          <div className="fixed right-6 bottom-6 z-50 hidden sm:block">
            <ThemeTogglerTwo />
          </div>
        </div>
      </ThemeProvider>
    </div>
  );
}
