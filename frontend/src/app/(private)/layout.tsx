"use client";

import { useSidebar } from "@/context/SidebarContext";
import AppHeader from "@/components/layout/AppHeader";
import AppSidebar from "@/components/layout/AppSidebar";
import Backdrop from "@/components/layout/Backdrop";
import RequireAuth from "@/components/auth/RequireAuth";
import React from "react";

type RootLayoutProps = {
    children: React.ReactNode;
};

export default function AdminLayout({
    children,
}: RootLayoutProps) {
    const { isExpanded, isHovered, isMobileOpen } = useSidebar();

    // Dynamic class for main content margin based on sidebar state
    const mainContentMargin = isMobileOpen
        ? "ml-0"
        : isExpanded || isHovered
            ? "lg:ml-[290px]"
            : "lg:ml-[90px]";

    return (
        <RequireAuth>
            <div className="min-h-screen xl:flex">
                {/* Sidebar and Backdrop */}
                <AppSidebar />
                <Backdrop />
                {/* Main Content Area */}
                <div
                    className={`flex-1 transition-all  duration-300 ease-in-out ${mainContentMargin}`}
                >
                    {/* Header */}
                    <AppHeader />
                    {/* Page Content */}
                    <div className="p-4 mx-auto max-w-(--breakpoint-2xl) md:p-6">{children}</div>
                </div>
            </div>
        </RequireAuth>
    );
}
