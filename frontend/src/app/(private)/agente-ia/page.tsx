import { Metadata } from "next";
import AgenteIAModule from "@/modules/agente-ia/AgenteIAModule";

export const metadata: Metadata = {
  title: "Agente IA - CINCO SAS",
  description: "Modulo principal del chat de IA DEV.",
};

const AgenteIAPage = () => {
  return <AgenteIAModule />;
};

export default AgenteIAPage;
