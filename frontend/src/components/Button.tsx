import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
	variant?: "primary" | "secondary" | "quiet" | "danger";
	icon?: ReactNode;
};

export default function Button({
	children,
	className = "",
	icon,
	type = "button",
	variant = "primary",
	...props
}: ButtonProps) {
	return (
		<button className={`button button-${variant} ${className}`.trim()} type={type} {...props}>
			{icon}
			{children}
		</button>
	);
}