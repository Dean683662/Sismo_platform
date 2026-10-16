import { BrowserRouter } from "react-router-dom";

import AuthProvider from "./AuthProvider";
import Layout from "./Layout";
import LoginView from "../modules/usuarios-roles/LoginView";
import { useAuth } from "../hooks/useAuth";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

function AppRoutes() {
	const { user, isLoading } = useAuth();
	const location = useLocation();

	if (isLoading) return <div className="auth-loading" role="status">Verificando sesión…</div>;

	return (
		<Routes>
			<Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginView />} />
			<Route path="/*" element={user ? <Layout /> : <Navigate to="/login" state={{ from: location }} replace />} />
		</Routes>
	);
}

export default function App() {
	return (
		<BrowserRouter>
			<AuthProvider>
				<AppRoutes />
			</AuthProvider>
		</BrowserRouter>
	);
}