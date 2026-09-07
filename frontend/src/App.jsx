import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import { rolesDe } from "./config/menu";
import RequireAuth from "./components/RequireAuth";
import RequireRol from "./components/RequireRol";
import LoginPage from "./pages/LoginPage";
import AppLayout from "./pages/AppLayout";
import GalponesPage from "./pages/GalponesPage";
import UsuariosPage from "./pages/UsuariosPage";
import StaticPage from "./pages/static/StaticPage";

import dashboardHtml from "./pages/static/raw/dashboard.html?raw";
import lotesHtml from "./pages/static/raw/lotes.html?raw";
import recoleccionHtml from "./pages/static/raw/recoleccion.html?raw";
import descartesHtml from "./pages/static/raw/descartes.html?raw";
import salidasHtml from "./pages/static/raw/salidas.html?raw";
import entradasHtml from "./pages/static/raw/entradas.html?raw";
import materiasPrimasHtml from "./pages/static/raw/materias-primas.html?raw";
import comprasHtml from "./pages/static/raw/compras.html?raw";
import proveedoresHtml from "./pages/static/raw/proveedores.html?raw";
import informesHtml from "./pages/static/raw/informes.html?raw";

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
          <Route path="lotes" element={<StaticPage html={lotesHtml} />} />
          <Route path="recoleccion" element={<StaticPage html={recoleccionHtml} />} />
          <Route path="descartes" element={<StaticPage html={descartesHtml} />} />
          <Route path="salidas" element={<StaticPage html={salidasHtml} />} />
          <Route path="entradas" element={<StaticPage html={entradasHtml} />} />
          <Route path="materias-primas" element={<StaticPage html={materiasPrimasHtml} />} />
          <Route path="compras" element={<RequireRol roles={rolesDe("/app/compras")}><StaticPage html={comprasHtml} /></RequireRol>} />
          <Route path="proveedores" element={<RequireRol roles={rolesDe("/app/proveedores")}><StaticPage html={proveedoresHtml} /></RequireRol>} />
          <Route path="informes" element={<StaticPage html={informesHtml} />} />
          <Route path="usuarios" element={<RequireRol roles={rolesDe("/app/usuarios")}><UsuariosPage /></RequireRol>} />
        </Route>
      </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
