import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

type ModalProps = {
	open: boolean;
	onClose: () => void;
	title: string;
	children: ReactNode;
};

export default function Modal({ open, onClose, title, children }: ModalProps) {
	const dialogRef = useRef<HTMLDialogElement>(null);
	const titleId = useId();

	useEffect(() => {
		const dialog = dialogRef.current;
		if (!dialog) return;

		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	}, [open]);

	return (
		<dialog
			aria-labelledby={titleId}
			className="modal"
			onCancel={(event) => {
				event.preventDefault();
				onClose();
			}}
			ref={dialogRef}
		>
			<header className="modal-header">
				<h2 id={titleId}>{title}</h2>
				<button aria-label="Cerrar ventana" className="icon-button" onClick={onClose} type="button">
					<X size={18} />
				</button>
			</header>
			<div className="modal-content">{children}</div>
		</dialog>
	);
}