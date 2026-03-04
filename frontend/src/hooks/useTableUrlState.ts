import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  SortingState,
  ColumnFiltersState,
  VisibilityState,
} from "@tanstack/react-table";

interface TableUrlStateConfig {
  defaultPageSize?: number;
  defaultPageIndex?: number;
  enableUrlSync?: boolean;
}

interface TableUrlState {
  globalFilter: string;
  columnFilters: ColumnFiltersState;
  sorting: SortingState;
  columnVisibility: VisibilityState;
  pageIndex: number;
  pageSize: number;
}

interface UseTableUrlStateReturn {
  globalFilter: string;
  setGlobalFilter: (value: string) => void;
  columnFilters: ColumnFiltersState;
  setColumnFilters: (filters: ColumnFiltersState) => void;
  sorting: SortingState;
  setSorting: (sorting: SortingState) => void;
  columnVisibility: VisibilityState;
  setColumnVisibility: (visibility: VisibilityState) => void;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
}

const parsePositiveInt = (
  value: string | null,
  fallback: number,
  minValue = 0,
): number => {
  if (!value) {
    return fallback;
  }

  const parsed = Number(value);

  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.max(Math.trunc(parsed), minValue);
};

const parseSortingParam = (value: string | null): SortingState => {
  if (!value) {
    return [];
  }

  const [columnId, direction] = value.split(":");

  if (!columnId || (direction !== "asc" && direction !== "desc")) {
    return [];
  }

  return [{ id: columnId, desc: direction === "desc" }];
};

const serializeSortingParam = (sorting: SortingState): string | null => {
  if (!sorting.length) {
    return null;
  }

  const [firstSort] = sorting;

  if (!firstSort?.id) {
    return null;
  }

  return `${firstSort.id}:${firstSort.desc ? "desc" : "asc"}`;
};

const parseUrlState = (
  searchParams: URLSearchParams,
  config: TableUrlStateConfig,
): TableUrlState => {
  return {
    globalFilter: searchParams.get("q") ?? "",
    columnFilters: [],
    sorting: parseSortingParam(searchParams.get("sort")),
    columnVisibility: {},
    pageIndex: parsePositiveInt(
      searchParams.get("p"),
      config.defaultPageIndex ?? 0,
      0,
    ),
    pageSize: parsePositiveInt(
      searchParams.get("ps"),
      config.defaultPageSize ?? 10,
      1,
    ),
  };
};

const buildUrlQuery = (
  currentSearchParams: URLSearchParams,
  state: Partial<TableUrlState>,
  config: TableUrlStateConfig,
): string => {
  const nextParams = new URLSearchParams(currentSearchParams.toString());

  if (state.globalFilter) {
    nextParams.set("q", state.globalFilter);
  } else {
    nextParams.delete("q");
  }

  if (state.pageIndex !== undefined && state.pageIndex > 0) {
    nextParams.set("p", String(state.pageIndex));
  } else {
    nextParams.delete("p");
  }

  if (
    state.pageSize !== undefined &&
    state.pageSize !== (config.defaultPageSize ?? 10)
  ) {
    nextParams.set("ps", String(state.pageSize));
  } else {
    nextParams.delete("ps");
  }

  if (state.sorting) {
    const sortValue = serializeSortingParam(state.sorting);
    if (sortValue) {
      nextParams.set("sort", sortValue);
    } else {
      nextParams.delete("sort");
    }
  }

  return nextParams.toString();
};

export const useTableUrlState = (
  config: TableUrlStateConfig = {},
): UseTableUrlStateReturn => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const enableUrlSync = config.enableUrlSync !== false;

  const initialState = useMemo(
    () => parseUrlState(new URLSearchParams(searchParams.toString()), config),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [searchParams],
  );

  const [globalFilter, setGlobalFilter] = useState(initialState.globalFilter);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>(
    initialState.columnFilters,
  );
  const [sorting, setSorting] = useState<SortingState>(initialState.sorting);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
    initialState.columnVisibility,
  );
  const [pageIndex, setPageIndex] = useState(initialState.pageIndex);
  const [pageSize, setPageSize] = useState(initialState.pageSize);

  useEffect(() => {
    setGlobalFilter(initialState.globalFilter);
    setSorting(initialState.sorting);
    setPageIndex(initialState.pageIndex);
    setPageSize(initialState.pageSize);
  }, [initialState]);

  useEffect(() => {
    if (!enableUrlSync) {
      return;
    }

    const nextQuery = buildUrlQuery(
      new URLSearchParams(searchParams.toString()),
      {
        globalFilter,
        pageIndex,
        pageSize,
        sorting,
      },
      config,
    );

    const currentQuery = searchParams.toString();
    if (nextQuery === currentQuery) {
      return;
    }

    const url = nextQuery ? `${pathname}?${nextQuery}` : pathname;
    router.replace(url, { scroll: false });
  }, [
    globalFilter,
    pageIndex,
    pageSize,
    sorting,
    pathname,
    router,
    searchParams,
    enableUrlSync,
    config,
  ]);

  return {
    globalFilter,
    setGlobalFilter,
    columnFilters,
    setColumnFilters,
    sorting,
    setSorting,
    columnVisibility,
    setColumnVisibility,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  };
};
