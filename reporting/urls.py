from django.urls import path

from .views import (
    access_log,
    add_report_configuration,
    add_report_recommendations,
    cancel_report_generation,
    copy_report_project,
    copy_report_recommendations,
    create_report_project,
    delete_report_project,
    delete_report_recommendation,
    download_report,
    download_template,
    edit_report_configuration,
    edit_report_project,
    generate_report_project,
    import_risk_analysis,
    report_configuration,
    report_generation_status,
    report_recommendations,
    reporting,
    review_comment_report,
    update_report_recommendation,
)

urlpatterns = [
    # Report generation
    path("", reporting, name="reporting"),
    # Report project
    path("project/create", create_report_project, name="create_report_project"),
    path(
        "project/<int:report_project_id>/copy",
        copy_report_project,
        name="copy_report_project",
    ),
    path(
        "project/<int:report_project_id>/edit",
        edit_report_project,
        name="edit_report_project",
    ),
    path(
        "project/<int:report_project_id>/delete",
        delete_report_project,
        name="delete_report_project",
    ),
    # Generate Reports
    path(
        "project/<int:report_project_id>/report/generate",
        generate_report_project,
        name="generate_report_project",
    ),
    # Download Reports
    path(
        "project/<int:report_project_id>/report/download/<uuid:file_uuid>",
        download_report,
        name="download_report",
    ),
    # Report generation status
    path(
        "project/<int:report_project_id>/report/status",
        report_generation_status,
        name="report_generation_status",
    ),
    # Cancel Report generation
    path(
        "project/<int:report_project_id>/report/cancel",
        cancel_report_generation,
        name="cancel_report_generation",
    ),
    # Configuration
    path("configuration", report_configuration, name="report_configuration"),
    path(
        "configuration/add", add_report_configuration, name="add_report_configuration"
    ),
    path(
        "configuration/edit/<int:report_configuration_id>",
        edit_report_configuration,
        name="edit_report_configuration",
    ),
    path(
        "recommendations/<int:company_id>/<int:sector_id>/<int:year>/",
        report_recommendations,
        name="report_recommendations",
    ),
    path(
        "review_comment_report/<int:company_id>/<int:sector_id>/<int:year>/",
        review_comment_report,
        name="review_comment_report",
    ),
    path(
        "recommendations/add/<int:company_id>/<int:sector_id>/<int:year>/",
        add_report_recommendations,
        name="add_report_recommendations",
    ),
    path(
        "recommendations/delete/<int:company_id>/<int:sector_id>/<int:year>/<int:report_rec_id>",
        delete_report_recommendation,
        name="delete_report_recommendations",
    ),
    path(
        "recommendations/copy/<int:company_id>/<int:sector_id>/<int:year>/",
        copy_report_recommendations,
        name="copy_report_recommendations",
    ),
    path(
        "recommendations/update/<int:report_rec_id>",
        update_report_recommendation,
        name="update_report_recommendation",
    ),
    path(
        "access_log/<int:company_id>/<int:sector_id>/<int:year>/",
        access_log,
        name="reporting_access_log",
    ),
    # Import risk analysis
    path("import_risk_analysis", import_risk_analysis, name="import_risk_analysis"),
    # Current template download
    path(
        "admin/reporting/template/<int:pk>/download/",
        download_template,
        name="reporting_template_download",
    ),
]
