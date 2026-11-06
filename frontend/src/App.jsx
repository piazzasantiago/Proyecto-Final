import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { DialogoProvider } from "./components/Dialogo";
import { rolesDe } from "./config/menu";
import RequireAuth from "./components/RequireAuth";
import RequireRol from "./components/RequireRol";
import LoginPage from "./pages/LoginPage";
import AppLayout from "./pages/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import GalponesPage from "./pages/GalponesPage";
import LotesPage from "./pages/LotesPage";
import ProductosPage from "./pages/ProductosPage";
import UsuariosPage from "./pages/UsuariosPage";
import RecoleccionesPage from "./pages/RecoleccionesPage";
import MateriaPrimasPage from "./pages/MateriaPrimasPage";
import DescartesPage from "./pages/DescartesPage";
import EntradasPage from "./pages/EntradasPage";
import SalidasPage from "./pages/SalidasPage";
import ProveedoresPage from "./pages/ProveedoresPage";
import InformesPage from "./pages/InformesPage";
import ComprasPage from "./pages/ComprasPage";

// Evita que la rueda del mouse cambie el valor de un campo numérico: los
// valores se escriben a mano, girar la rueda sobre un campo no tiene que
// modificarlo sin querer.
//
// Se escucha en la fase de captura y con passive: false porque hace falta
// llegar antes que el navegador y poder cancelar el evento; quitarle el foco
// al campo no alcanza, el navegador ya aplicó el cambio. Después de blur() el
// preventDefault corta ese movimiento de rueda y la página sigue haciendo
// scroll normal con el siguiente.
//
// La bandera evita registrar el listener dos veces si el módulo se recarga.
if (typeof window !== "undefined" && !window.__sinRuedaNumerica) {
  window.__sinRuedaNumerica = true;
  window.addEventListener(
    "wheel",
    (evento) => {
      const el = evento.target;
      if (
        el instanceof HTMLInputElement &&
        el.type === "number" &&
        document.activeElement === el
      ) {
        el.blur();
        evento.preventDefault();
      }
    },
    { capture: true, passive: false }
  );
}

function App() {
  return (
    <BrowserRouter>
      {/* AuthProvider envuelve todo: la sesión queda disponible en cualquier página. */}
      <AuthProvider>
      {/* Cuadros de confirmación y aviso propios (en lugar de confirm/alert del navegador). */}
      <DialogoProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        {/* Todo lo que cuelga de /app exige sesión iniciada. */}
        <Route
          path="/app"
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="galpones" element={<GalponesPage />} />
          <Route path="lotes" element={<LotesPage />} />
          <Route path="productos" element={<RequireRol roles={rolesDe("/app/productos")}><ProductosPage /></RequireRol>} />
          <Route path="recoleccion" element={<RecoleccionesPage />} />
          <Route path="materias-primas" element={<RequireRol roles={rolesDe("/app/materias-primas")}><MateriaPrimasPage /></RequireRol>} />
          <Route path="descartes" element={<DescartesPage />} />
          <Route path="salidas" element={<SalidasPage />} />
          <Route path="entradas" element={<EntradasPage />} />
          <Route path="compras" element={<RequireRol roles={rolesDe("/app/compras")}><ComprasPage /></RequireRol>} />
          <Route path="proveedores" element={<RequireRol roles={rolesDe("/app/proveedores")}><ProveedoresPage /></RequireRol>} />
          <Route path="informes" element={<RequireRol roles={rolesDe("/app/informes")}><InformesPage /></RequireRol>} />
          <Route path="usuarios" element={<RequireRol roles={rolesDe("/app/usuarios")}><UsuariosPage /></RequireRol>} />
        </Route>
      </Routes>
      </DialogoProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
