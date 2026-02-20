"use client";

import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    getFilteredRowModel,
    getSortedRowModel,
    useReactTable,
    SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import type { ColumnFiltersState } from "@tanstack/react-table";

import {
    Table,
    TableBody,
    TableCell,
    TableHeader,
    TableRow,
} from "../ui/table";
import Input from "../form/input/InputField";
import { DataTableProps } from "@/types/table";

export function DataTable<TData>({
    data,
    columns,
    isLoading = false,
    emptyMessage = "No data available",
    enablePagination = true,
    pageSize = 10,
    enableGlobalFilter = false,
    enableColumnFilters = false,
    enableSorting = false,
    pageSizeOptions = [10, 20, 50],
}: DataTableProps<TData>) {
    const [globalFilter, setGlobalFilter] = useState("");
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [sorting, setSorting] = useState<SortingState>([]);

    const table = useReactTable({
        data,
        columns,
        state: {
            globalFilter,
            columnFilters,
            sorting,
        },
        onGlobalFilterChange: setGlobalFilter,
        onColumnFiltersChange: setColumnFilters,
        onSortingChange: setSorting,
        getCoreRowModel: getCoreRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
        ...(enablePagination && { getPaginationRowModel: getPaginationRowModel() }),
        initialState: {
            pagination: {
                pageSize,
                pageIndex: 0,
            },
        },
    });

    return (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/5 dark:bg-white/3">
            {/* GLOBAL FILTER */}
            {enableGlobalFilter && (
                <div className="p-4 flex justify-end">
                    <Input
                        type="search"
                        placeholder="Search..."
                        // value={globalFilter ?? ""}
                        onChange={(e) => setGlobalFilter(e.target.value)}
                        className="w-60"
                    />
                </div>
            )}

            <div className="overflow-x-auto">
                <Table>
                    <TableHeader className="border-b border-gray-100 dark:border-white/5">
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableCell
                                        key={header.id}
                                        isHeader
                                        className="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400"
                                    >
                                        {/* HEADER */}
                                        <span
                                            className={enableSorting ? "cursor-pointer select-none" : ""}
                                            onClick={
                                                enableSorting
                                                    ? header.column.getToggleSortingHandler()
                                                    : undefined
                                            }
                                            style={enableSorting ? { display: "inline-block", width: "100%" } : undefined}
                                        >
                                            {flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                            {/* ICONO DE ORDEN */}
                                            {enableSorting &&
                                                header.column.getIsSorted() &&
                                                (header.column.getIsSorted() === "asc"
                                                    ? " 🔼"
                                                    : " 🔽")}
                                        </span>
                                        {/* FILTRO POR COLUMNA */}
                                        {enableColumnFilters && header.column.getCanFilter() && (
                                            <div className="mt-1">
                                                <Input
                                                    type="search"
                                                    onChange={(e) =>
                                                        header.column.setFilterValue(e.target.value)
                                                    }
                                                    placeholder="Filter..."
                                                    className="w-full px-2 py-1 border rounded-md text-xs"
                                                />
                                            </div>
                                        )}
                                    </TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>

                    <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                        {isLoading ? (
                            <TableRow>
                                <TableCell className="px-6 py-8 text-center text-gray-500">
                                    Loading...
                                </TableCell>
                            </TableRow>
                        ) : table.getRowModel().rows.length === 0 ? (
                            <TableRow>
                                <TableCell className="px-6 py-8 text-center text-gray-500">
                                    {emptyMessage}
                                </TableCell>
                            </TableRow>
                        ) : (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={row.id}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell
                                            key={cell.id}
                                            className="px-4 py-3 text-gray-500 text-start text-theme-sm dark:text-gray-400"
                                        >
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
            {enablePagination && (
                <div className="flex items-center justify-between px-5 py-4 border-t">
                    <div className="flex items-center justify-between w-full gap-3">
                        {pageSizeOptions && (
                            <select
                                value={table.getState().pagination.pageSize}
                                onChange={(e) => {
                                    table.setPageSize(Number(e.target.value));
                                    table.setPageIndex(0);
                                }}
                                className="px-2 py-1 border rounded text-sm"
                            >
                                {pageSizeOptions.map((size) => (
                                    <option key={size} value={size}>
                                        {size}
                                    </option>
                                ))}
                            </select>
                        )}

                        <div className="flex gap-2 items-center">
                            <button
                                onClick={() => table.previousPage()}
                                disabled={!table.getCanPreviousPage()}
                                className="px-3 py-1 border rounded disabled:opacity-50"
                            >
                                Anterior
                            </button>
                            <span className="text-sm text-gray-500">
                                Página {table.getState().pagination.pageIndex + 1} de{" "}
                                {table.getPageCount()}
                            </span>
                            <button
                                onClick={() => table.nextPage()}
                                disabled={!table.getCanNextPage()}
                                className="px-3 py-1 border rounded disabled:opacity-50"
                            >
                                Siguiente
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
