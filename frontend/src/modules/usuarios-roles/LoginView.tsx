import { useState, type FormEvent } from "react";
import { Activity, ArrowRight, ShieldCheck } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../../hooks/useAuth";

export default function LoginView() {
	const { login } = useAuth();
	const location = useLocation();
	const navigate = useNavigate();
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [error, setError] = useState("");
	const [submitting, setSubmitting] = useState(false);
	const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/";

	async function handleSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError("");
		setSubmitting(true);
		try {
			await login(email, password);
			navigate(from, { replace: true });
		} catch {
			setError("No se pudo iniciar sesión. Revisa tus credenciales o intenta más tarde.");
		} finally {
			setSubmitting(false);
		}
	}

	return (
		<main className="login-page">
			<section className="login-brand-panel">
				<div className="login-brand">
					<span className="brand-mark"><Activity size={20} strokeWidth={2.4} /></span>
					<span className="brand-name">sismo<span>.</span><small>OBSERVATORIO</small></span>
				</div>
				<div className="login-brand-copy">
					<div className="page-eyebrow"><span className="live-mark" /> MONITOREO Y ANALÍTICA</div>
					<h1>Información sísmica, con trazabilidad.</h1>
					<p>Acceso interno para consultar eventos observados, análisis y operación de la plataforma.</p>
				</div>
				<div className="login-privacy"><ShieldCheck size={16} /><span>Acceso administrado por roles</span></div>
			</section>
			<section className="login-form-panel">
				<form className="login-form" onSubmit={handleSubmit}>
					<div className="login-form-heading">
						<div className="panel-kicker">PLATAFORMA INTERNA</div>
						<h2>Iniciar sesión</h2>
						<p>Ingresa con la cuenta asignada por el administrador.</p>
					</div>
					<label htmlFor="login-email">Correo electrónico</label>
					<input autoComplete="username" id="login-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
					<label htmlFor="login-password">Contraseña</label>
					<input autoComplete="current-password" id="login-password" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
					{error && <p className="form-error" role="alert">{error}</p>}
					<button className="login-submit" disabled={submitting} type="submit"><span>{submitting ? "Validando…" : "Continuar"}</span><ArrowRight size={17} /></button>
					<p className="login-disclaimer">Los accesos y cambios administrativos quedan registrados en la bitácora.</p>
				</form>
				<footer className="login-footer">SISMO · Plataforma de monitoreo sísmico</footer>
			</section>
		</main>
	);
}