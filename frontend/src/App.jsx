import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AppLayout from "./pages/AppLayout";
import GalponesPage from "./pages/GalponesPage";
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
import usuariosHtml from "./pages/static/raw/usuarios.html?raw";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<StaticPage html={dashboardHtml} />} />
          <Route path="galpones" element={<GalponesPage />} />
          <Route path="lotes" element={<StaticPage html={lotesHtml} />} />
          <Route path="recoleccion" element={<StaticPage html={recoleccionHtml} />} />
          <Route path="descartes" element={<StaticPage html={descartesHtml} />} />
          <Route path="salidas" element={<StaticPage html={salidasHtml} />} />
          <Route path="entradas" element={<StaticPage html={entradasHtml} />} />
          <Route path="materias-primas" element={<StaticPage html={materiasPrimasHtml} />} />
          <Route path="compras" element={<StaticPage html={comprasHtml} />} />
          <Route path="proveedores" element={<StaticPage html={proveedoresHtml} />} />
          <Route path="informes" element={<StaticPage html={informesHtml} />} />
          <Route path="usuarios" element={<StaticPage html={usuariosHtml} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
