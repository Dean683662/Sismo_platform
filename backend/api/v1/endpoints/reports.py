"""Create immutable, filtered report snapshots and export them as JSON or CSV."""

import csv
import io
import json
from datetime import datetime, timezone
from uuid import UUID

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.v1.schemas import ReportCreateRequest, ReportResponse
from backend.core.database import get_db
from backend.core.security import require_csrf, require_permissions
from backend.database.models import ReportRun, User
from backend.services.audit_service import record_audit
from backend.services.report_generator import generate_report_records


router = APIRouter(prefix="/reports", tags=["reports"])


def _utc(value: datetime | None) -> datetime | None:
	if value is None:
		return None
	return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _report_response(report: ReportRun, requested_by: str | None) -> ReportResponse:
	return ReportResponse(
		id=str(report.id),
		report_type=report.report_type,
		filters=report.filters,
		row_count=report.row_count,
		requested_by=requested_by,
		created_at=report.created_at,
	)


def _stringify(value: object) -> str:
	if value is None:
		return ""
	if isinstance(value, (dict, list)):
		return json.dumps(value, ensure_ascii=False, sort_keys=True)
	return str(value)


def _spreadsheet_safe(value: object) -> object:
	if isinstance(value, str) and value.lstrip(" \t\r\n")[:1] in {"=", "+", "-", "@"}:
		return f"'{value}"
	return value


def _xlsx_export(report: ReportRun, requester: str | None) -> bytes:
	workbook = Workbook()
	data_sheet = workbook.active
	data_sheet.title = "Datos"
	fieldnames = list(dict.fromkeys(key for row in report.records_json for key in row))
	if fieldnames:
		data_sheet.append([_spreadsheet_safe(fieldname) for fieldname in fieldnames])
		for cell in data_sheet[1]:
			cell.font = Font(bold=True, color="FFFFFF")
			cell.fill = PatternFill("solid", fgColor="146F68")
		for row in report.records_json:
			data_sheet.append([_spreadsheet_safe(_xlsx_value(row.get(field))) for field in fieldnames])
		data_sheet.freeze_panes = "A2"
		data_sheet.auto_filter.ref = data_sheet.dimensions
		for column in data_sheet.columns:
			width = min(48, max(12, max(len(str(cell.value or "")) for cell in column) + 2))
			data_sheet.column_dimensions[column[0].column_letter].width = width
	else:
		data_sheet.append(["Sin registros para los filtros seleccionados"])
	metadata = workbook.create_sheet("Metadatos")
	metadata.append(["Campo", "Valor"])
	metadata.append(["ID del reporte", str(report.id)])
	metadata.append(["Tipo", report.report_type])
	metadata.append(["Solicitante", requester or "Usuario eliminado"])
	metadata.append(["Fecha de generación UTC", report.created_at.isoformat()])
	metadata.append(["Fecha de corte UTC", str(report.filters.get("cutoff_at", ""))])
	metadata.append(["Número de filas", report.row_count])
	metadata.append(["Filtros", json.dumps(report.filters, ensure_ascii=False, sort_keys=True)])
	for cell in metadata[1]:
		cell.font = Font(bold=True, color="FFFFFF")
		cell.fill = PatternFill("solid", fgColor="146F68")
	metadata.column_dimensions["A"].width = 26
	metadata.column_dimensions["B"].width = 100
	metadata["B8"].alignment = Alignment(wrap_text=True, vertical="top")
	buffer = io.BytesIO()
	workbook.save(buffer)
	return buffer.getvalue()


def _xlsx_value(value: object) -> object:
	if isinstance(value, (dict, list)):
		return json.dumps(value, ensure_ascii=False, sort_keys=True)
	return value


def _pdf_export(report: ReportRun, requester: str | None) -> bytes:
	buffer = io.BytesIO()
	document = SimpleDocTemplate(
		buffer,
		pagesize=landscape(A3),
		rightMargin=12 * mm,
		leftMargin=12 * mm,
		topMargin=14 * mm,
		bottomMargin=14 * mm,
		title=f"Reporte {report.report_type}",
	)
	styles = getSampleStyleSheet()
	body_style = ParagraphStyle("ReportCell", parent=styles["BodyText"], fontName="Helvetica", fontSize=6, leading=7, alignment=TA_LEFT, wordWrap="CJK")
	header_style = ParagraphStyle("ReportHeader", parent=body_style, fontName="Helvetica-Bold", textColor=colors.white)
	elements = [
		Paragraph(f"Reporte: {report.report_type}", styles["Title"]),
		Paragraph(f"Solicitante: {requester or 'Usuario eliminado'}", styles["BodyText"]),
		Paragraph(f"Generado (UTC): {report.created_at.isoformat()} · Corte (UTC): {report.filters.get('cutoff_at', '')}", styles["BodyText"]),
		Paragraph(f"Filas: {report.row_count} · Filtros: {_escape_pdf(json.dumps(report.filters, ensure_ascii=False, sort_keys=True))}", body_style),
		Spacer(1, 5 * mm),
	]
	fieldnames = list(dict.fromkeys(key for row in report.records_json for key in row))
	if not fieldnames:
		elements.append(Paragraph("No hay registros para los filtros seleccionados.", styles["BodyText"]))
	else:
		table_data = [[Paragraph(_escape_pdf(key), header_style) for key in fieldnames]]
		for record in report.records_json:
			table_data.append([Paragraph(_escape_pdf(_stringify(record.get(field))), body_style) for field in fieldnames])
		available_width = landscape(A3)[0] - document.leftMargin - document.rightMargin
		column_width = available_width / len(fieldnames)
		table = LongTable(table_data, colWidths=[column_width] * len(fieldnames), repeatRows=1, splitByRow=1)
		table.setStyle(TableStyle([
			("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#146f68")),
			("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
			("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ccd8d4")),
			("VALIGN", (0, 0), (-1, -1), "TOP"),
			("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6f4")]),
			("LEFTPADDING", (0, 0), (-1, -1), 3),
			("RIGHTPADDING", (0, 0), (-1, -1), 3),
			("TOPPADDING", (0, 0), (-1, -1), 3),
			("BOTTOMPADDING", (0, 0), (-1, -1), 3),
		]))
		elements.append(table)
	document.build(elements)
	return buffer.getvalue()


def _escape_pdf(value: str) -> str:
	from xml.sax.saxutils import escape

	return escape(value).replace("\n", "<br/>")


@router.post(
	"",
	response_model=ReportResponse,
	status_code=status.HTTP_201_CREATED,
	dependencies=[Depends(require_csrf)],
)
def create_report(
	request: ReportCreateRequest,
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("reports:read")),
) -> ReportResponse:
	generated_at = datetime.now(timezone.utc)
	records = generate_report_records(db, request, generated_at)
	filters = {
		"start_date": _utc(request.start_date).isoformat() if request.start_date else None,
		"end_date": _utc(request.end_date).isoformat() if request.end_date else None,
		"min_magnitude": request.min_magnitude,
		"max_magnitude": request.max_magnitude,
		"source_key": request.source_key,
		"limit": request.limit,
		"cutoff_at": generated_at.isoformat(),
	}
	report = ReportRun(
		report_type=request.report_type,
		filters=filters,
		row_count=len(records),
		records_json=records,
		created_by=actor.id,
		created_at=generated_at,
	)
	db.add(report)
	db.flush()
	record_audit(
		db,
		actor_id=actor.id,
		action="reports.snapshot_created",
		entity_type="report",
		entity_id=report.id,
		after={"report_type": report.report_type, "row_count": report.row_count, "filters": filters},
	)
	db.commit()
	db.refresh(report)
	return _report_response(report, actor.email)


@router.get("", response_model=list[ReportResponse])
def list_reports(
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
	_: User = Depends(require_permissions("reports:read")),
) -> list[ReportResponse]:
	rows = db.execute(
		select(ReportRun, User.email)
		.outerjoin(User, User.id == ReportRun.created_by)
		.order_by(ReportRun.created_at.desc())
		.limit(limit)
	).all()
	return [_report_response(report, email) for report, email in rows]


@router.get("/{report_id}/export")
def export_report(
	report_id: UUID,
	export_format: str = Query(default="csv", alias="format", pattern="^(csv|json|xlsx|pdf)$"),
	db: Session = Depends(get_db),
	actor: User = Depends(require_permissions("reports:read")),
) -> Response:
	report = db.get(ReportRun, report_id)
	if report is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
	requester = db.scalar(select(User.email).where(User.id == report.created_by)) if report.created_by else None
	record_audit(
		db,
		actor_id=actor.id,
		action="reports.exported",
		entity_type="report",
		entity_id=report.id,
		after={"format": export_format},
	)
	db.commit()
	filename = f"report-{report.report_type}-{report.id}"
	if export_format == "json":
		content = json.dumps(
			{
				"id": str(report.id),
				"report_type": report.report_type,
				"filters": report.filters,
				"row_count": report.row_count,
				"requested_by": requester,
				"created_at": report.created_at.isoformat(),
				"records": report.records_json,
			},
			ensure_ascii=False,
			indent=2,
		)
		return Response(
			content=content,
			media_type="application/json; charset=utf-8",
			headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
		)
	if export_format == "xlsx":
		return Response(
			content=_xlsx_export(report, requester),
			media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
			headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
		)
	if export_format == "pdf":
		return Response(
			content=_pdf_export(report, requester),
			media_type="application/pdf",
			headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
		)

	buffer = io.StringIO(newline="")
	if report.records_json:
		fieldnames = list(dict.fromkeys(key for row in report.records_json for key in row))
		writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
		writer.writeheader()
		for row in report.records_json:
			safe_row = {
				key: f"'{value}"
				if isinstance(value, str) and value.lstrip(" \t\r\n")[:1] in {"=", "+", "-", "@"}
				else value
				for key, value in row.items()
			}
			writer.writerow(safe_row)
	content = "\ufeff" + buffer.getvalue()
	return Response(
		content=content,
		media_type="text/csv; charset=utf-8",
		headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
	)