import { Metadata } from "next";
import IADevWorkspace from "@/modules/programacion/ia-dev/IADevWorkspace";

export const metadata: Metadata = {
  title: "IA DEV - CINCO SAS",
  description: "Modulo IA DEV.",
};

const IADevPage = () => {
  return <IADevWorkspace />;
};

export default IADevPage;
