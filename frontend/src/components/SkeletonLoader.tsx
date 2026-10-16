type SkeletonLoaderProps = {
	lines?: number;
	className?: string;
};

export default function SkeletonLoader({ lines = 3, className = "" }: SkeletonLoaderProps) {
	return (
		<div aria-busy="true" aria-label="Cargando contenido" className={`skeleton-group ${className}`.trim()} role="status">
			{Array.from({ length: Math.max(1, lines) }, (_, index) => (
				<span className="skeleton-line" key={index} />
			))}
		</div>
	);
}