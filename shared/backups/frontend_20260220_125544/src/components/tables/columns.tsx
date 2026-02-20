import { ColumnDef } from "@tanstack/react-table";
import Image from "next/image";
import Badge from "../ui/badge/Badge";

export interface Order {
  id: number;
  user: {
    image: string;
    name: string;
    role: string;
  };
  projectName: string;
  team: {
    images: string[];
  };
  status: string;
  budget: string;
}

export const orderColumns: ColumnDef<Order>[] = [
  {
    header: "User",
    cell: ({ row }) => {
      const user = row.original.user;
      return (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 overflow-hidden rounded-full">
            <Image src={user.image} width={40} height={40} alt={user.name} />
          </div>
          <div>
            <span className="block font-medium text-gray-800 dark:text-white/90">
              {user.name}
            </span>
            <span className="block text-gray-500 text-theme-xs">
              {user.role}
            </span>
          </div>
        </div>
      );
    },
  },
  {
    header: "Project Name",
    accessorKey: "projectName",
  },
  {
    header: "Team",
    cell: ({ row }) => (
      <div className="flex -space-x-2">
        {row.original.team.images.map((img, i) => (
          <div
            key={i}
            className="w-6 h-6 overflow-hidden border-2 border-white rounded-full"
          >
            <Image src={img} width={24} height={24} alt="" />
          </div>
        ))}
      </div>
    ),
  },
  {
    header: "Status",
    cell: ({ row }) => (
      <Badge
        size="sm"
        color={
          row.original.status === "Active"
            ? "success"
            : row.original.status === "Pending"
            ? "warning"
            : "error"
        }
      >
        {row.original.status}
      </Badge>
    ),
  },
  {
    header: "Budget",
    accessorKey: "budget",
  },
];
