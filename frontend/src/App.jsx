import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { rolesDe } from "./config/menu";
import RequireAuth from "./components/RequireAuth";
import RequireRol from "./components/RequireRol";
import LoginPage from "./pages/LoginPage";
import AppLayout from "./pages/AppLayout";
import GalponesPage from "./pages/GalponesPage";
import LotesPage from "./pages/LotesPage";
import ProductosPage from "./pages/ProductosPage";
import UsuariosPage from "./pages/UsuariosPage";
import RecoleccionesPage from "./pages/RecoleccionesPage";
import MateriaPrimasPage from "./pages/MateriaPrimasPage";
import DescartesPage from "./pages/DescartesPage";
import EntradasPage from "./pages/EntradasPage";
import SalidasPage from "./pages/SalidasPage";
import StaticPage from "./pages/static/StaticPage";
import ProveedoresPage from "./pages/ProveedoresPage";
import InformesPage from "./pages/InformesPage";
import ComprasPage from "./pages/ComprasPage";

import dashboardHtml from "./pages/static/raw/dashboard.html?raw";

function App() {
  return (
    <BrowserRouter>
      {/* AuthProvider envuelve todo: la sesión queda disponible en cualquier página. */}
      <AuthProvider>
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
          <Route path="dashboard" element={<StaticPage html={dashboardHtml} />} />
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
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
