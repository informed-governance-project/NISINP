from django.urls import path

from .views import (
    access_log,
    add_report_configuration,
    add_report_recommendations,
    copy_report_recommendations,
    delete_report_recommendation,
    edit_report_configuration,
    import_risk_analysis,
    report_configuration,
    report_recommendations,
    reporting,
    review_comment_report,
)

urlpatterns = [
    # Report generation
    path("", reporting, name="reporting"),
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
        "access_log/<int:company_id>/<int:sector_id>/<int:year>/",
        access_log,
        name="reporting_access_log",
    ),
    # Import risk analysis
    path("import_risk_analysis", import_risk_analysis, name="import_risk_analysis"),
]
