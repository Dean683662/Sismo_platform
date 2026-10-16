import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLElement> & {
	title?: string;
	description?: string;
	action?: ReactNode;
};

export default function Card({
	action,
	children,
	className = "",
	description,
	title,
	...props
}: CardProps) {
	return (
		<section className={`card ${className}`.trim()} {...props}>
			{(title || description || action) && (
				<header className="card-header">
					<div>
						{title && <h2>{title}</h2>}
						{description && <p>{description}</p>}
					</div>
					{action}
				</header>
			)}
			{children}
		</section>
	);
}