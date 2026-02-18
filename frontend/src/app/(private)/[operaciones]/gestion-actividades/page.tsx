import { Metadata } from "next";
import GestionActividadesView from "@/modules/operaciones/actividad/gestionActividadesView";

export const metadata: Metadata = {
    title: "Gestión de Actividades - CINCO SAS",
    description: "Modulo de gestión de actividades de CINCO SAS.",
};

const HomePage = () => {
    return (
        <GestionActividadesView />
    );
}
export default HomePage;