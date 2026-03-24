import base64
import copy
import datetime
import os
import re
import shutil
import subprocess
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import formats
from django.utils.translation import activate
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage, RichTextParagraph
from lxml import etree

from .globals import TRANSLATIONS_CONTEXT
from .helpers import (
    convert_docx_to_pdf,
    create_entry_log,
    fix_outer_column_borders,
    get_charts,
    get_risk_data,
    get_so_data,
    merge_subdoc_into_placeholder,
    redistribute_column_widths_proportional,
)
from .models import Configuration, GeneratedReport, Project, Template


def extract_toc_page_numbers_v2(doc_v2: Document) -> dict[str, str]:
    body = doc_v2.element.body
    paragraphs = list(body.iter(qn("w:p")))

    results = dict()

    in_toc = False

    for para in paragraphs:
        pStyle = para.find(".//" + qn("w:pStyle"))
        style_val = pStyle.get(qn("w:val"), "") if pStyle is not None else ""

        if not in_toc:
            for instr in para.iter(qn("w:instrText")):
                if "TOC" in (instr.text or ""):
                    in_toc = True
                    break

        if not in_toc:
            continue

        # end of TOC : fldChar[end] on a non-TOC para
        if not style_val.upper().startswith("TOC"):
            fld_chars = list(para.iter(qn("w:fldChar")))
            if any(fc.get(qn("w:fldCharType")) == "end" for fc in fld_chars):
                break
            # Para without style TOC but with fldChar end in the last hyperlink
            for hl in para.iter(qn("w:hyperlink")):
                for r in hl.iter(qn("w:r")):
                    fc = r.find(qn("w:fldChar"))
                    if fc is not None and fc.get(qn("w:fldCharType")) == "end":
                        in_toc = False
                        break

        for hyperlink in para.iter(qn("w:hyperlink")):
            for r in hyperlink.iter(qn("w:r")):
                texts = list(r.iter(qn("w:t")))

                if len(texts) >= 2:
                    before_last = texts[-2].text.strip()
                    last = texts[-1].text.strip()
                    results[before_last] = last

    return results


# replace ToC number of v1 by the v2
def replace_toc_page_numbers(doc_v1: Document, doc_v2: Document) -> None:
    title_number = extract_toc_page_numbers_v2(doc_v2)
    print("page numbers")
    print(title_number)

    body = doc_v1.element.body
    paragraphs = list(body.iter(qn("w:p")))
    in_toc = False

    for para in paragraphs:
        title = None
        pStyle = para.find(".//" + qn("w:pStyle"))
        style_val = pStyle.get(qn("w:val"), "") if pStyle is not None else ""

        if not in_toc:
            for instr in para.iter(qn("w:instrText")):
                if "TOC" in (instr.text or ""):
                    in_toc = True
                    break

        if not in_toc:
            continue

        # Detect end of Toc paragraphe NO_STYLE with fldChar[end] of TOC global field
        if not style_val.startswith("TOC") and not style_val.startswith("toc"):
            has_toc_instr = any(
                "TOC" in (instr.text or "") for instr in para.iter(qn("w:instrText"))
            )
            if not has_toc_instr:
                # check if it's the fldChar[end] of global ToC
                fld_chars = list(para.iter(qn("w:fldChar")))
                if any(fc.get(qn("w:fldCharType")) == "end" for fc in fld_chars):
                    break
                # we continue
                if not any(para.iter(qn("w:hyperlink"))):
                    continue
        title = extract_title_from_para(para)
        # in each ToC, empty the w:t after fldChar[separate] od PAGEREF
        if title and title in title_number:
            for hyperlink in para.iter(qn("w:hyperlink")):
                in_pageref_value = False
                for r in hyperlink.iter(qn("w:r")):
                    fld_char = r.find(qn("w:fldChar"))
                    if fld_char is not None:
                        fld_type = fld_char.get(qn("w:fldCharType"))
                        if fld_type == "separate":
                            in_pageref_value = True
                        elif fld_type == "end":
                            in_pageref_value = False

                    if in_pageref_value:
                        t = r.find(qn("w:t"))
                        if t is not None:
                            t.text = title_number[title]


# extract the title of a docx paragraph
def extract_title_from_para(para):
    texts = [t.text.strip() for t in para.iter(qn("w:t")) if t.text and t.text.strip()]

    if len(texts) < 2:
        return None

    # remove the last (page number)
    texts_no_page = texts[:-1]

    # remove the begning (ex : 1.2.3)
    clean_texts = [t for t in texts_no_page if not re.match(r"^\d+(\.\d+)*$", t)]

    if not clean_texts:
        return None

    # real title = last one
    texte = " ".join(clean_texts)
    print(texte)
    return " ".join(texte.split())


# update page number with libre office
def old_update_toc(file_path: str):
    """
    Update table of content in docx
    """

    cmd = [
        "/usr/bin/python3",
        "/home/monarc/governanceplatform/reporting/scripts/update_toc_docx.py",
        file_path,
    ]

    subprocess.run(
        cmd,
        check=True,
        timeout=30,
    )


# dump ToC structure in libre office doc
def dump_toc_structure(doc: Document, output_path: str = "toc_dump.txt"):
    body = doc.element.body
    paragraphs = list(body.iter(qn("w:p")))

    in_toc = False
    with open(output_path, "w", encoding="utf-8") as f:
        for i, para in enumerate(paragraphs):
            for instr in para.iter(qn("w:instrText")):
                if "TOC" in (instr.text or ""):
                    in_toc = True

            if in_toc:
                pStyle = para.find(".//" + qn("w:pStyle"))
                style = (
                    pStyle.get(qn("w:val"), "") if pStyle is not None else "NO_STYLE"
                )
                f.write(f"\n--- Para {i} | style: {style} ---\n")
                f.write(etree.tostring(para, pretty_print=True).decode())

                if (
                    pStyle is not None
                    and "TOC" not in style
                    and "toc" not in style.lower()
                ):
                    if i > 0:
                        in_toc = False
                        break


# remove page number in ToC in word document
def remove_page_numbers_from_toc(doc: Document):
    body = doc.element.body
    paragraphs = list(body.iter(qn("w:p")))

    in_toc = False

    for para in paragraphs:
        pStyle = para.find(".//" + qn("w:pStyle"))
        style_val = pStyle.get(qn("w:val"), "") if pStyle is not None else ""

        # detect begining of ToC
        if not in_toc:
            for instr in para.iter(qn("w:instrText")):
                if "TOC" in (instr.text or ""):
                    in_toc = True
                    break

        if not in_toc:
            continue

        # Detect end of Toc paragraphe NO_STYLE with fldChar[end] of TOC global field
        if not style_val.startswith("TOC") and not style_val.startswith("toc"):
            has_toc_instr = any(
                "TOC" in (instr.text or "") for instr in para.iter(qn("w:instrText"))
            )
            if not has_toc_instr:
                # check if it's the fldChar[end] of global ToC
                fld_chars = list(para.iter(qn("w:fldChar")))
                if any(fc.get(qn("w:fldCharType")) == "end" for fc in fld_chars):
                    break
                # we continue
                if not any(para.iter(qn("w:hyperlink"))):
                    continue

        # in each ToC, empty the w:t after fldChar[separate] od PAGEREF
        for hyperlink in para.iter(qn("w:hyperlink")):
            in_pageref_value = False
            for r in hyperlink.iter(qn("w:r")):
                fld_char = r.find(qn("w:fldChar"))
                if fld_char is not None:
                    fld_type = fld_char.get(qn("w:fldCharType"))
                    if fld_type == "separate":
                        in_pageref_value = True
                    elif fld_type == "end":
                        in_pageref_value = False

                if in_pageref_value:
                    t = r.find(qn("w:t"))
                    if t is not None:
                        t.text = ""


@shared_task
def generate_data(cleaned_data):
    project_id = cleaned_data["project_id"]
    if Project.objects.get(id=project_id).task_status == "ABORT":
        return
    language = cleaned_data.get("language", "en")
    activate(language)
    report_configuration_id = cleaned_data["report_configuration_id"]
    colors = Configuration.objects.get(pk=report_configuration_id).colors.values_list(
        "color"
    )
    template_id = cleaned_data["template_id"]
    so_data = get_so_data(cleaned_data)
    risk_data = get_risk_data(cleaned_data)
    charts = get_charts(so_data, risk_data, colors)

    data = {
        "company": cleaned_data["company"]["name"],
        "years": cleaned_data["years"],
        "reference_year": cleaned_data["reference_year"],
        "sector": cleaned_data["sector"]["name"],
        "threshold_for_high_risk": cleaned_data["threshold_for_high_risk"],
        "top_ranking": cleaned_data["top_ranking"],
        "report_recommendations": cleaned_data["report_recommendations"],
        "charts": charts,
        "so_data": so_data,
        "risk_data": risk_data,
        "company_reporting": cleaned_data["company_reporting"],
        "translations": {k: str(v) for k, v in TRANSLATIONS_CONTEXT.items()},
        "template_id": template_id,
        "project_id": project_id,
    }

    return data


@shared_task(bind=True)
def generate_docx_task(self, data):
    if not data:
        return
    project_id = data["project_id"]
    if Project.objects.get(id=project_id).task_status == "ABORT":
        return
    tmp_id = str(self.request.id)
    base_tmp_dir = Path(settings.PATH_FOR_REPORTING_PDF)
    task_tmp_dir = base_tmp_dir / str(project_id) / "tmp_files" / tmp_id
    subdocs_templates_dir = Path(
        os.path.join(settings.BASE_DIR, "reporting", "subdocs_templates")
    )
    task_tmp_dir.mkdir(parents=True, exist_ok=True)
    template_id = data["template_id"]
    template_file = Template.objects.get(pk=template_id).template_file
    template_path = BytesIO(bytes(template_file))
    rendered_subs_docs = {}
    nb_years = len(data["years"])
    document_charts = {
        "chart_average_risk_level": {
            "width": Mm(140),
        },
        "chart_high_risk_rate": {
            "width": Mm(140),
        },
        "chart_average_high_risk_level": {
            "width": Mm(140),
        },
        "chart_evolution_highest_risks": {
            "width": Mm(140),
        },
    }
    document_tables = {
        "table_of_evolution_security_objectives": {
            "context": {
                "table": data["so_data"]["company_so_by_year"],
            },
            "column_proportions": [0.4] + [0.1] * nb_years + [0.15],
        },
        "table_of_evolution_security_objectives_by_domain": {
            "context": {
                "table": data["so_data"]["company_so_by_domain"],
            },
            "column_proportions": [0.4] + [0.1] * nb_years + [0.15] * 2,
        },
        "table_of_highest_security_objectives_in_the_sector": {
            "context": {
                "table": data["so_data"]["sector_so_by_year_desc"][
                    str(data["reference_year"])
                ],
            },
            "column_proportions": [0.05] + [0.65] + [0.15] * 2,
        },
        "table_of_lowest_security_objectives_in_the_sector": {
            "context": {
                "table": data["so_data"]["sector_so_by_year_asc"][
                    str(data["reference_year"])
                ],
            },
            "column_proportions": [0.05] + [0.65] + [0.15] * 2,
        },
        "table_of_evolution_of_the_weakest_security_objectives": {
            "context": {
                "table": data["so_data"]["company_so_by_priority"],
            },
            "column_proportions": [0.4] + [0.15] * nb_years + [0.15],
        },
        "table_of_security_objectives_by_maturity_level": {
            "context": {
                "table": data["so_data"]["company_so_by_level"],
            },
            "column_proportions": [0.25]
            * len(data["so_data"]["company_so_by_level"]["headers"]),
        },
        "maturity_level_legend": {
            "context": {
                "maturity_levels": data["so_data"]["maturity_levels"],
            },
        },
        "table_of_evolution_of_the_highest_risks": {
            "context": {
                "table": data["risk_data"]["data_risks_top_ranking"],
            },
            "column_proportions": [0.1, 0.25, 0.25, 0.3] + [0.1] * nb_years,
        },
        "table_of_treatment_of_the_highest_risks": {
            "context": {
                "table": data["risk_data"]["data_risks_top_ranking"],
            },
            "column_proportions": [0.08, 0.18, 0.18, 0.25, 0.13, 0.17, 0.13],
        },
        "table_of_risk_summary": {
            "context": {
                "table": data["risk_data"]["risks_stats_by_year"],
            },
            "column_proportions": [0.7] + [0.15] * nb_years,
            "table_width_dxa": 7380,  # 13cm
        },
        "table_of_top_threats_by_occurrence": {
            "context": {
                "table": data["risk_data"]["top_threats"],
            },
            "column_proportions": [0.1, 0.9],
            "table_width_dxa": 8504,  # 15cm
        },
        "table_of_top_vulnerabilities_by_occurrence": {
            "context": {
                "table": data["risk_data"]["top_vulnerabilities"],
            },
            "column_proportions": [0.1, 0.9],
            "table_width_dxa": 8504,  # 15cm
        },
        "table_of_recommendations": {
            "context": {
                "table": data["risk_data"]["recommendations_evolution"],
            },
            "column_proportions": [0.7, 0.15, 0.15],
        },
    }

    main_doc_template = DocxTemplate(template_path)
    main_doc = Document(template_path)

    report_recommendations = RichTextParagraph()
    for rec in data["report_recommendations"]:
        report_recommendations.add(rec, parastyle="CircleBullet")

    context = {
        "operator_name": data["company"],
        "sector": data["sector"],
        "year": data["reference_year"],
        "threshold_for_high_risk": data["threshold_for_high_risk"],
        "top_ranking": data["top_ranking"],
        "report_recommendations": report_recommendations,
        "report_observations": data["company_reporting"]["comment"],
        "publication_date": formats.date_format(datetime.date.today(), format="d F Y"),
    }
    for chart_name, chart_data in data["charts"].items():
        chart_bytes = BytesIO(base64.b64decode(chart_data))
        chart_with = document_charts.get(chart_name, {}).get("width", Mm(170))
        context[chart_name] = InlineImage(
            main_doc_template, chart_bytes, width=chart_with
        )
    if not task_tmp_dir.exists():
        return

    for table_name, table_info in document_tables.items():
        sub_template_path = subdocs_templates_dir / f"{table_name}_template.docx"
        sub_rendered_path = task_tmp_dir / f"{table_name}_rendered.docx"
        context[table_name] = str(table_name)
        table_info["context"].update(
            {
                "translations": data["translations"],
                "year": data["reference_year"],
                "years": data["years"],
            }
        )
        sub_doc_template = DocxTemplate(sub_template_path)
        sub_doc_template.render(table_info["context"])
        sub_doc_template.save(sub_rendered_path)
        sub_doc = Document(sub_rendered_path)
        for table in sub_doc.tables:
            table_width_dxa = None
            if "table_width_dxa" in table_info:
                # 1dxa = 1cm * 28.346 * 20
                table_width_dxa = table_info["table_width_dxa"]
            if "column_proportions" in table_info:
                redistribute_column_widths_proportional(
                    table, table_info["column_proportions"], main_doc, table_width_dxa
                )
            fix_outer_column_borders(table._element)
        sub_doc.save(sub_rendered_path)
        rendered_subs_docs[table_name] = sub_rendered_path

    main_docx_path = Path(task_tmp_dir / "main_doc.docx")
    main_doc_template.render(context)
    main_doc_template.save(main_docx_path)
    current_doc = main_docx_path
    tmp_output_path = task_tmp_dir / "tmp_doc.docx"

    for placeholder, sub_rendered_path in rendered_subs_docs.items():
        sub_rendered_path = Path(sub_rendered_path)
        try:
            merge_subdoc_into_placeholder(
                main_docx_path=current_doc,
                subdoc_path=sub_rendered_path,
                placeholder=placeholder,
                output_path=tmp_output_path,
            )
            current_doc = tmp_output_path
        finally:
            if sub_rendered_path.exists():
                sub_rendered_path.unlink(missing_ok=True)

    main_docx_path.unlink(missing_ok=True)
    return {"file_path": str(current_doc), "project_id": project_id}


@shared_task
def generate_pdf_task(data):
    project_id = data["project_id"]
    if Project.objects.get(id=project_id).task_status == "ABORT":
        return
    docx_path = Path(data["file_path"])

    if not docx_path.exists():
        return
    try:
        doc = Document(str(docx_path))
        # copy the current doc
        doc2 = copy.deepcopy(doc)
        doc2.save(str(docx_path.with_suffix(".lo.docx")))
        # update number
        old_update_toc(str(docx_path.with_suffix(".lo.docx")))

        doc = Document(str(docx_path))
        doc2 = Document(str(docx_path.with_suffix(".lo.docx")))

        # replace with the correct number
        replace_toc_page_numbers(doc, doc2)
        doc.save(str(docx_path))
        pdf_path = convert_docx_to_pdf(str(docx_path))
        return {"file_path": str(pdf_path), "project_id": project_id}

    finally:
        if docx_path.exists():
            docx_path.unlink(missing_ok=True)


@shared_task
def save_file_task(data, run_id, user_id, filename, is_multiple_files):
    if not data:
        return
    project_id = data["project_id"]
    project = Project.objects.get(id=project_id)
    if project.task_status == "ABORT":
        return
    temp_file_path = data["file_path"]
    file_uuid = uuid.uuid4()
    User = get_user_model()
    user = User.objects.get(id=user_id)
    output_dir = Path(os.path.join(settings.PATH_FOR_REPORTING_PDF, str(project_id)))
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, str(file_uuid))

    if is_multiple_files:
        temp_output_dir = os.path.join(output_dir, run_id)
        os.makedirs(temp_output_dir, exist_ok=True)
        file_path = os.path.join(temp_output_dir, filename)

    else:
        GeneratedReport.objects.update_or_create(
            project=project,
            defaults={"file_uuid": file_uuid, "filename": filename},
        )
        create_entry_log(user, project, "GENERATE REPORT")
        project.task_status = "DONE"
        project.save()

    shutil.move(temp_file_path, file_path)
    parent_dir = Path(temp_file_path).parent
    shutil.rmtree(parent_dir)

    if output_dir.exists():
        for item in output_dir.iterdir():
            if str(item.name) != str(file_uuid) and not item.is_dir():
                item.unlink()

    return {"file_path": str(file_path), "user_id": user_id, "project_id": project_id}


@shared_task
def zip_files_task(data, error_messages):
    if not data[0]:
        return
    User = get_user_model()
    user = User.objects.get(id=data[0]["user_id"])
    project_id = data[0]["project_id"]
    file_paths = [item["file_path"] for item in data]
    project = Project.objects.get(id=project_id)
    if project.task_status == "ABORT":
        return
    file_uuid = uuid.uuid4()
    output_dir = Path(os.path.join(settings.PATH_FOR_REPORTING_PDF, str(project_id)))
    if output_dir.exists() and output_dir.is_dir():
        for item in output_dir.iterdir():
            if item.is_file():
                item.unlink()
    zip_filename = f"reports_{project.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path = os.path.join(output_dir, str(file_uuid))

    if not isinstance(file_paths, list):
        file_paths = [file_paths]

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in file_paths:
            if os.path.exists(file_path):
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname=arcname)
            else:
                print(f"File not found: {file_path}")

        if error_messages:
            error_log = "\n".join(error_messages)
            zipf.writestr("error_log.txt", error_log)

    temp_dir = os.path.dirname(file_paths[0])

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    GeneratedReport.objects.update_or_create(
        project=project,
        defaults={"file_uuid": file_uuid, "filename": zip_filename},
    )
    create_entry_log(user, project, "GENERATE REPORT")
    project.task_status = "DONE"
    project.save()

    return zip_path


@shared_task(ignore_result=True)
def cleanup_files(project_id, all_files=False):
    base_tmp_dir = Path(settings.PATH_FOR_REPORTING_PDF)
    task_tmp_dir = base_tmp_dir / str(project_id)

    if all_files and task_tmp_dir.exists():
        shutil.rmtree(task_tmp_dir)
        return

    if task_tmp_dir.exists() and task_tmp_dir.is_dir():
        for item in task_tmp_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
