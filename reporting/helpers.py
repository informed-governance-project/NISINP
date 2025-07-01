import base64
import textwrap
import uuid
from collections import Counter, OrderedDict, defaultdict
from io import BytesIO
from statistics import mean
from typing import List

import plotly.colors as pc
import plotly.graph_objects as go
from django.db.models import Avg, Count, F, Min, OuterRef, Subquery
from django.db.models.functions import Floor
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _
from parler.models import TranslationDoesNotExist

from securityobjectives.models import (
    Domain,
    MaturityLevel,
    SecurityObjective,
    SecurityObjectiveStatus,
    StandardAnswer,
)

from .globals import SECTOR_LEGEND
from .models import AssetData, LogReporting, RecommendationData, RiskData, ServiceStat


def get_so_data(cleaned_data):
    def get_latest_answers(company, sector, year):
        latest_submit_date = (
            StandardAnswer.objects.filter(
                submitter_company=OuterRef("submitter_company"),
                sectors__id__in=[sector["id"]],
                year_of_submission=year,
                status="PASS",
            )
            .order_by("-submit_date")
            .values("submit_date")[:1]
        )

        queryset = StandardAnswer.objects.filter(
            sectors__id__in=[sector["id"]],
            year_of_submission=year,
            status="PASS",
            submit_date=Subquery(latest_submit_date),
        ).distinct()

        if company is not None:
            queryset = queryset.filter(submitter_company__id=company["id"])

        return queryset

    def calculate_evolution(previous_data, current_score):
        if previous_data:
            previous_score = previous_data["score"]
            if previous_score > current_score:
                return False
            elif previous_score < current_score:
                return True
        return None

    def build_dict_scores(queryset, target_dict, key_func, year, sector_values=False):
        for item in queryset:
            key = key_func(item)
            score_field = "score_value"

            if isinstance(item, dict):
                score = item[score_field]
            else:
                score = getattr(item, score_field)

            if sector_values:
                target_dict[key][year]["sector_avg"] = score
            else:
                previous_year = year - 1
                previous_data = target_dict[key].get(previous_year)
                evolution = calculate_evolution(previous_data, score)
                target_dict[key][year] = {
                    "score": score,
                    "evolution": evolution,
                }

    def build_radar_data(data_dict, sector_avg_field=None):
        radar_data = defaultdict()
        score_field = "score"
        for __key, years in data_dict.items():
            for year, values in years.items():
                year_label = f"{company['name']} {year}"
                radar_data.setdefault(year_label, []).append(values[score_field])

                if sector_avg_field and year == current_year:
                    radar_data.setdefault(f"{SECTOR_LEGEND} {current_year}", []).append(
                        values[sector_avg_field]
                    )

        return dict(radar_data)

    def build_bar_chart_by_level_data(counts, label):
        levels_count = maturity_levels_queryset.count()
        score_list = [counts.get(level, 0) for level in range(levels_count)]
        bar_chart_data_by_level[label] = score_list

    company = cleaned_data["company"]
    sector = cleaned_data["sector"]
    current_year = cleaned_data["year"]
    nb_years = cleaned_data["nb_years"]
    so_excluded = cleaned_data["so_excluded"]
    top_ranking = cleaned_data["top_ranking"]
    maturity_levels_queryset = MaturityLevel.objects.order_by("level")
    maturity_levels = [str(level) for level in maturity_levels_queryset]
    years_list = []
    sector_so_by_year_desc = OrderedDict()
    sector_so_by_year_asc = OrderedDict()
    bar_chart_data_by_level = defaultdict()
    company_so_by_year = defaultdict(lambda: {})
    company_so_by_domain = defaultdict(lambda: {})
    company_so_by_priority = defaultdict(lambda: {})
    radar_chart_data_by_domain = defaultdict()
    radar_chart_data_by_year = defaultdict()
    so_data = defaultdict()

    for offset in range(nb_years):
        year = current_year - nb_years + offset + 1
        company_so_by_level = defaultdict(list)
        latest_answers = get_latest_answers(company, sector, year)

        if latest_answers.exists():
            years_list.append(year)

        # Company Querysets
        # TO DO : manage the case when it's empty
        floored_company_queryset = (
            SecurityObjectiveStatus.objects.filter(standard_answer__in=latest_answers)
            .exclude(security_objective__in=[so["id"] for so in so_excluded])
            .annotate(score_value=Floor(F("score")))
        )

        so_domain_company_queryset = (
            floored_company_queryset.values("security_objective__domain")
            .annotate(score_value=Avg("score"))
            .order_by("security_objective__domain")
        )

        sorted_company_queryset = floored_company_queryset.annotate(
            min_position=Min(
                "security_objective__securityobjectivesinstandard__position"
            )
        )

        company_by_priority_queryset = floored_company_queryset.annotate(
            min_priority=Min(
                "security_objective__securityobjectivesinstandard__priority"
            )
        ).order_by("score_value", "min_priority")

        aggregated_scores_queryset = floored_company_queryset.values(
            "score_value"
        ).annotate(count=Count("score_value"))

        # Sector Querysets

        latest_answers_sector = get_latest_answers(None, sector, year)

        sector_queryset = SecurityObjectiveStatus.objects.filter(
            standard_answer__in=latest_answers_sector
        ).exclude(security_objective__in=[so["id"] for so in so_excluded])

        sector_score_by_domain_queryset = (
            sector_queryset.values("security_objective__domain")
            .annotate(score_value=Avg("score"))
            .order_by("security_objective__domain")
        )

        sector_scores_queryset = sector_queryset.values("security_objective").annotate(
            score_value=Floor(Avg("score")),
            min_position=Min(
                "security_objective__securityobjectivesinstandard__position"
            ),
        )

        # Dictionaries

        # by_level
        for score_data in sorted_company_queryset.order_by(
            "score_value", "min_position"
        ):
            level = maturity_levels_queryset.filter(
                level=int(score_data.score_value)
            ).first()
            security_objective = score_data.security_objective
            company_so_by_level[str(level)].append(security_objective)

        # by_domain
        build_dict_scores(
            so_domain_company_queryset,
            company_so_by_domain,
            lambda x: Domain.objects.get(pk=x["security_objective__domain"]),
            year,
        )

        # by_domain [sector]
        build_dict_scores(
            sector_score_by_domain_queryset,
            company_so_by_domain,
            lambda x: Domain.objects.get(pk=x["security_objective__domain"]),
            year,
            True,
        )

        # by_year
        build_dict_scores(
            sorted_company_queryset.order_by("min_position"),
            company_so_by_year,
            lambda x: x.security_objective,
            year,
        )

        # by_priority
        build_dict_scores(
            company_by_priority_queryset,
            company_so_by_priority,
            lambda x: x.security_objective,
            year,
        )

        # Bar chart by level
        company_counts = Counter(
            {
                score_data["score_value"]: score_data["count"]
                for score_data in aggregated_scores_queryset
            }
        )

        sector_counts = Counter(
            {
                score_data["score_value"]: sector_scores_queryset.filter(
                    score_value=score_data["score_value"]
                ).count()
                for score_data in sector_scores_queryset
            }
        )

        build_bar_chart_by_level_data(
            counts=company_counts,
            label=f"{company['name']} {year}",
        )

        build_bar_chart_by_level_data(
            counts=sector_counts,
            label=f"{SECTOR_LEGEND} {year}",
        )

        # Sector asc and desc lists by score
        sector_so_by_year_asc[year] = [
            SecurityObjective.objects.get(pk=score["security_objective"])
            for score in sector_scores_queryset.order_by("score_value", "min_position")[
                :top_ranking
            ]
        ]

        sector_so_by_year_desc[year] = [
            SecurityObjective.objects.get(pk=score["security_objective"])
            for score in sector_scores_queryset.order_by(
                "-score_value", "min_position"
            )[:top_ranking]
        ]

    radar_chart_data_by_domain = build_radar_data(company_so_by_domain, "sector_avg")
    radar_chart_data_by_year = build_radar_data(company_so_by_year)

    so_data = {
        "years": years_list,
        "domains": [str(domain) for domain in company_so_by_domain.keys()],
        "maturity_levels": maturity_levels,
        "unique_codes_list": [so.unique_code for so in company_so_by_year.keys()],
        "max_of_company_count": max(company_counts.values()),
        "bar_chart_data_by_level": dict(sort_legends(bar_chart_data_by_level)),
        "company_so_by_level": dict(company_so_by_level),
        "company_so_by_domain": dict(company_so_by_domain),
        "company_so_by_year": dict(company_so_by_year),
        "company_so_by_priority": dict(company_so_by_priority),
        "sector_so_by_year_desc": dict(sector_so_by_year_desc),
        "sector_so_by_year_asc": dict(sector_so_by_year_asc),
        "radar_chart_data_by_domain": radar_chart_data_by_domain,
        "radar_chart_data_by_year": radar_chart_data_by_year,
    }

    return so_data


def get_risk_data(cleaned_data):
    def build_risk_average_data(service):
        service_stat_queryset = ServiceStat.objects.filter(
            service=service,
            company_reporting__year=year,
            company_reporting__sector__id=sector_id,
        )

        average_risks_by_sector = service_stat_queryset.aggregate(
            avg_current_risks=Avg("avg_current_risks")
        )["avg_current_risks"]

        servicestat_by_company = service_stat_queryset.filter(
            company_reporting__company__id=company_id,
        )

        average_risks_by_company = (
            servicestat_by_company.first().avg_current_risks
            if servicestat_by_company
            else 0
        )

        for label in labels:
            data_by_risk_average.setdefault(label, [])

        data_by_risk_average[company_label].append(
            round_value(average_risks_by_company)
        )

        data_by_risk_average[sector_label].append(round_value(average_risks_by_sector))

    def build_high_risk_data(service):
        # Querysets
        risk_data_service_queryset = RiskData.objects.filter(
            service__service=service,
            service__company_reporting__year=year,
            service__company_reporting__sector__id=sector_id,
            max_risk__gt=threshold_for_high_risk,
        ).exclude(risk_treatment="UNTRE")

        service_stat_queryset = ServiceStat.objects.filter(
            service=service,
            company_reporting__year=year,
            company_reporting__company__id=company_id,
            company_reporting__sector__id=sector_id,
        )

        high_risks_by_company = risk_data_service_queryset.filter(
            service__company_reporting__company__id=company_id,
        ).aggregate(count=Count("id"), max_risk_avg=Avg("max_risk"))

        high_risks_average_by_sector = risk_data_service_queryset.aggregate(
            max_risk_avg=Avg("max_risk")
        )

        # High risk rate data
        total_high_risks = high_risks_by_company["count"]

        total_risk = (
            service_stat_queryset.first().total_treated_risks
            if service_stat_queryset
            else 0
        )

        rate = (total_high_risks / total_risk) if total_risk else 0

        data_by_high_risk_rate.setdefault(year, {"rate_labels": [], "rate_values": []})

        data_by_high_risk_rate[year]["rate_labels"].append(
            f"{total_high_risks} / {total_risk}"
        )
        data_by_high_risk_rate[year]["rate_values"].append(rate)

        # High risk average data
        for label in labels:
            data_by_high_risk_average.setdefault(label, [])

        data_by_high_risk_average[company_label].append(
            round_value(high_risks_by_company["max_risk_avg"])
        )
        data_by_high_risk_average[sector_label].append(
            round_value(high_risks_average_by_sector["max_risk_avg"])
        )

        # Stats by service data
        service_stats.setdefault(service, {year: {}})
        if service_stat_queryset:
            service_stats[service][year] = model_to_dict(service_stat_queryset.first())
            service_stats[service][year]["total_high_risks_treated"] = total_high_risks
            service_stats[service][year][
                "avg_high_risks_treated"
            ] = high_risks_by_company["max_risk_avg"]
        else:
            service_stats[service][year] = {}

    def build_evolution_highest_risks_data(company_reporting):
        risks_data = (
            RiskData.objects.filter(
                service__company_reporting__id=company_reporting["id"],
            )
            .exclude(risk_treatment="UNTRE")
            .annotate(total_impact=F("impact_c") + F("impact_i") + F("impact_a"))
            .order_by(
                "-max_risk",
                "-total_impact",
                "-threat_value",
                "-vulnerability_value",
                "asset__translations__name",
            )
        )

        top_ranking_distinct_risks = get_top_ranking_distinct_risks(
            risks_data, top_ranking
        )

        data_evolution_highest_risks[f"{company['name']} {current_year}"] = [
            round_value(risk.max_risk) for risk in top_ranking_distinct_risks
        ]

        i = 1
        past_year = current_year - nb_years + i
        while i <= nb_years:
            i += 1
            for risk in top_ranking_distinct_risks:
                uuid = risk.uuid
                if uuid not in risks_top_ranking:
                    risks_top_ranking_ids.append(f"R{risk.id}")
                    risks_top_ranking[uuid] = model_to_dict(risk)
                    risks_top_ranking[uuid][
                        "treatment"
                    ] = risk.get_risk_treatment_display()
                    risks_top_ranking[uuid]["service"] = str(risk.service.service)
                    risks_top_ranking[uuid]["asset"] = str(risk.asset)
                    risks_top_ranking[uuid]["threat"] = str(risk.threat)
                    risks_top_ranking[uuid]["vulnerability"] = str(risk.vulnerability)
                    risks_top_ranking[uuid]["impacts"] = {
                        current_year: {
                            "c": (
                                {"value": risk.impact_c if risk.impact_c > -1 else None}
                            ),
                            "i": (
                                {"value": risk.impact_i if risk.impact_i > -1 else None}
                            ),
                            "a": (
                                {"value": risk.impact_a if risk.impact_a > -1 else None}
                            ),
                        }
                    }
                    risks_top_ranking[uuid]["threat_values"] = {
                        current_year: {
                            "value": (
                                risk.threat_value if risk.threat_value > -1 else None
                            )
                        }
                    }
                    risks_top_ranking[uuid]["vulnerability_values"] = {
                        current_year: {
                            "value": (
                                risk.vulnerability_value
                                if risk.vulnerability_value > -1
                                else None
                            )
                        }
                    }
                    risks_top_ranking[uuid]["risks_values"] = {
                        current_year: {
                            "c": ({"value": risk.risk_c if risk.risk_c > -1 else None}),
                            "i": ({"value": risk.risk_i if risk.risk_i > -1 else None}),
                            "a": ({"value": risk.risk_a if risk.risk_a > -1 else None}),
                        }
                    }

                if past_year == current_year:
                    continue

                try:
                    risk = RiskData.objects.get(
                        uuid=uuid,
                        service__service=risk.service.service,
                        service__company_reporting__year=past_year,
                        service__company_reporting__company__id=company_id,
                        service__company_reporting__sector__id=sector_id,
                    )

                    max_risk = risk.max_risk

                    impacts_dict = {
                        "c": ({"value": risk.impact_c if risk.impact_c > -1 else None}),
                        "i": ({"value": risk.impact_i if risk.impact_i > -1 else None}),
                        "a": ({"value": risk.impact_a if risk.impact_a > -1 else None}),
                    }

                    threat_value = {
                        "value": risk.threat_value if risk.threat_value > -1 else None
                    }

                    vulnerability_value = {
                        "value": (
                            risk.vulnerability_value
                            if risk.vulnerability_value > -1
                            else None
                        )
                    }

                    risk_values_dict = {
                        "c": ({"value": risk.risk_c if risk.risk_c > -1 else None}),
                        "i": ({"value": risk.risk_i if risk.risk_i > -1 else None}),
                        "a": ({"value": risk.risk_a if risk.risk_a > -1 else None}),
                    }

                    if past_year == current_year - 1:
                        values_changed = False
                        current_ranking = risks_top_ranking[uuid]

                        # Compare impacts
                        current_year_impacts = current_ranking["impacts"][current_year]
                        for key, impact in current_year_impacts.items():
                            impact_changed = (
                                impacts_dict[key]["value"] != impact["value"]
                            )
                            impact["changed"] = impact_changed
                            values_changed = values_changed or impact_changed

                        # Compare threat
                        current_year_threat = current_ranking["threat_values"][
                            current_year
                        ]
                        threat_changed = (
                            risk.threat_value != current_year_threat["value"]
                        )
                        current_year_threat["changed"] = threat_changed
                        values_changed = values_changed or threat_changed

                        # Compare vulnerability
                        current_year_vulnerability = current_ranking[
                            "vulnerability_values"
                        ][current_year]
                        vulnerability_changed = (
                            risk.vulnerability_value
                            != current_year_vulnerability["value"]
                        )
                        current_year_vulnerability["changed"] = vulnerability_changed
                        values_changed = values_changed or vulnerability_changed

                        # Compare risks if any previous value is different
                        if values_changed:
                            current_year_risks = current_ranking["risks_values"][
                                current_year
                            ]
                            filtered_values = [
                                item["value"]
                                for item in current_year_risks.values()
                                if item["value"] is not None
                            ]
                            current_max_value = max(filtered_values, default=None)

                            for key, risk_item in current_year_risks.items():
                                risk_values_dict[key]["changed"] = (
                                    risk_values_dict[key]["value"] == max_risk
                                )
                                risk_item["changed"] = (
                                    risk_item["value"] == current_max_value
                                )

                except RiskData.DoesNotExist:
                    max_risk = 0
                    impacts_dict = {
                        "c": None,
                        "i": None,
                        "a": None,
                    }
                    threat_value = None
                    vulnerability_value = None
                    risk_values_dict = {
                        "c": None,
                        "i": None,
                        "a": None,
                    }

                risks_top_ranking[uuid]["impacts"][past_year] = impacts_dict
                risks_top_ranking[uuid]["threat_values"][past_year] = threat_value
                risks_top_ranking[uuid]["vulnerability_values"][
                    past_year
                ] = vulnerability_value
                risks_top_ranking[uuid]["risks_values"][past_year] = risk_values_dict

                data_evolution_highest_risks[f"{company['name']} {past_year}"].append(
                    round_value(max_risk)
                )

            past_year += 1

    def build_top_ranking_risk_items(service, is_last=False):
        def get_distinct_sorted(data, sort_key, id_key):
            seen = set()
            return [
                item
                for item in sorted(
                    data, key=lambda x: get_nested_attr(x, sort_key), reverse=True
                )
                if not (
                    get_nested_attr(item, id_key) in seen
                    or seen.add(get_nested_attr(item, id_key))
                )
            ]

        def get_sorted_data(data, sort_id_pairs):
            return {
                name: get_distinct_sorted(data, sort_key=key, id_key=id)
                for name, (key, id) in sort_id_pairs.items()
            }

        def append_top_ranking(data, sort_id_pairs, target_key):
            for index in range(top_ranking):
                ranking_dict = {
                    key: data[key][index]
                    for key in sort_id_pairs.keys()
                    if index < len(data[key])
                }
                top_ranking_risks_items[target_key].append(ranking_dict)

        risk_data_reporting_queryset = (
            RiskData.objects.filter(
                service__company_reporting__year=year,
                service__company_reporting__sector__id=sector_id,
                service__company_reporting__company__id=company_id,
            )
            .exclude(risk_treatment="UNTRE")
            .annotate(total_impact=F("impact_c") + F("impact_i") + F("impact_a"))
        )

        risk_data_service_queryset = risk_data_reporting_queryset.filter(
            service__service=service
        )

        data = list(risk_data_service_queryset)
        if not data:
            return

        sort_id_pairs = {
            "threat_by_max_risk": ("max_risk", "threat_id"),
            "vulnerability_by_max_risk": ("max_risk", "vulnerability_id"),
            "asset_by_max_risk": ("max_risk", "asset.name"),
            "threat_by_residual_risk": ("residual_risk", "threat_id"),
            "vulnerability_by_residual_risk": (
                "residual_risk",
                "vulnerability_id",
            ),
            "asset_by_residual_risk": ("residual_risk", "asset.name"),
            "by_threat": ("threat_value", "threat_id"),
            "by_vulnerability": ("vulnerability_value", "vulnerability_id"),
            "by_asset": ("total_impact", "asset.name"),
        }

        sorted_data = get_sorted_data(data, sort_id_pairs)
        append_top_ranking(sorted_data, sort_id_pairs, service)

        if is_last:
            all_data = list(risk_data_reporting_queryset)
            if all_data:
                all_service_sorted_data = get_sorted_data(all_data, sort_id_pairs)
                append_top_ranking(
                    all_service_sorted_data, sort_id_pairs, _("All services")
                )

    def build_recommendations_data(company_reporting):
        return (
            RecommendationData.objects.filter(
                riskdata__service__company_reporting__id=company_reporting["id"]
            )
            .annotate(risk_count=Count("riskdata"))
            .order_by("-risk_count")[:top_ranking]
        )

    def build_evolution_recommendations_data():
        recommendations_by_year = RecommendationData.objects.filter(
            riskdata__service__company_reporting__year=year,
            riskdata__service__company_reporting__company__id=company_id,
            riskdata__service__company_reporting__sector__id=sector_id,
        )

        if recommendations_by_year:
            for recommendation in recommendations_by_year:
                recommendation_key = generate_combined_uuid(
                    [recommendation.code, recommendation.description]
                )
                recommendations_evolution.setdefault(
                    recommendation_key,
                    {
                        "code": recommendation.code,
                        "description": recommendation.description,
                    },
                )

                previous_year = year - 1
                previous_due_date = recommendations_evolution[recommendation_key].get(
                    previous_year
                )

                if previous_due_date:
                    status = _("Postponed")
                    if (
                        previous_due_date == recommendation.due_date
                        and recommendation.due_date.year == previous_year
                    ):
                        status = _("To check")
                else:
                    status = _("Open") if year == current_year else _("Closed")

                recommendations_evolution[recommendation_key]["status"] = status
                recommendations_evolution[recommendation_key][
                    year
                ] = recommendation.due_date

    company = cleaned_data["company"]
    company_id = company["id"]
    sector = cleaned_data["sector"]
    sector_id = sector["id"]
    current_year = cleaned_data["year"]
    nb_years = cleaned_data["nb_years"]
    years_list = []
    threshold_for_high_risk = cleaned_data["threshold_for_high_risk"]
    top_ranking = cleaned_data["top_ranking"]
    company_reporting = cleaned_data["company_reporting"]
    data_by_risk_average = defaultdict()
    data_by_high_risk_rate = defaultdict()
    data_by_high_risk_average = defaultdict()
    data_evolution_highest_risks = defaultdict(lambda: [])
    risks_top_ranking = OrderedDict()
    risks_top_ranking_ids = []
    service_stats = OrderedDict()
    top_ranking_risks_items = defaultdict(lambda: [])
    recommendations_evolution = defaultdict(lambda: {})
    services_list = (
        AssetData.objects.filter(
            servicestat__company_reporting__id=company_reporting["id"]
        )
        .order_by("id")
        .distinct()
    )
    operator_services = [str(service) for service in services_list]
    operator_services_with_all = [_("All services")] + operator_services

    for offset in range(nb_years):
        year = current_year - nb_years + offset + 1
        years_list.append(year)
        company_label = f"{company['name']} {year}"
        sector_label = f"{SECTOR_LEGEND} {year}"
        labels = [company_label, sector_label]

        for index, service in enumerate(services_list):
            build_risk_average_data(service)
            build_high_risk_data(service)

            if year == current_year:
                is_last = index == len(services_list) - 1
                build_top_ranking_risk_items(service, is_last)

        # Score mean for all services
        for label in labels:
            data_by_risk_average[label].insert(
                0, round_value(mean(data_by_risk_average[label]))
            )
            data_by_high_risk_average[label].insert(
                0, round_value(mean(data_by_high_risk_average[label]))
            )

        if year == current_year:
            build_evolution_highest_risks_data(company_reporting)
            most_recommendations_used = build_recommendations_data(company_reporting)

        build_evolution_recommendations_data()

    risk_data = {
        "years": years_list,
        "threshold_for_high_risk": threshold_for_high_risk,
        "data_by_risk_average": dict(sort_legends(data_by_risk_average)),
        "data_by_high_risk_rate": dict(data_by_high_risk_rate),
        "data_by_high_risk_average": dict(sort_legends(data_by_high_risk_average)),
        "data_evolution_highest_risks": dict(
            sort_legends(data_evolution_highest_risks)
        ),
        "data_risks_top_ranking": list(
            values for uuid, values in risks_top_ranking.items()
        ),
        "risks_top_ranking_ids": risks_top_ranking_ids,
        "service_stats": dict(service_stats),
        "top_ranking_risks_items": dict(top_ranking_risks_items),
        "most_recommendations_used": most_recommendations_used,
        "recommendations_evolution": dict(recommendations_evolution),
        "operator_services": operator_services,
        "operator_services_with_all": operator_services_with_all,
    }

    return risk_data


def get_charts(so_data, risk_data):
    charts = {
        "colorbar": generate_colorbar(),
        "security_measures_1": generate_bar_chart(
            so_data["bar_chart_data_by_level"], so_data["maturity_levels"]
        ),
        "security_measures_5a": generate_radar_chart(
            so_data["radar_chart_data_by_domain"],
            so_data["domains"],
            so_data["maturity_levels"],
        ),
        "security_measures_5b": generate_radar_chart(
            so_data["radar_chart_data_by_year"],
            so_data["unique_codes_list"],
            so_data["maturity_levels"],
        ),
        "risks_1": generate_bar_chart(
            risk_data["data_by_risk_average"], risk_data["operator_services_with_all"]
        ),
        "risks_2": generate_bar_chart(
            risk_data["data_by_high_risk_rate"], risk_data["operator_services"], True
        ),
        "risks_3": generate_bar_chart(
            risk_data["data_by_high_risk_average"],
            risk_data["operator_services_with_all"],
        ),
        "risks_4": generate_bar_chart(
            risk_data["data_evolution_highest_risks"],
            risk_data["risks_top_ranking_ids"],
        ),
    }

    return charts


def sort_legends(data):
    return sorted(
        data.items(),
        key=lambda x: (x[0] != SECTOR_LEGEND, x[0]),
    )


def round_value(value):
    if value is None:
        return 0

    if isinstance(value, int):
        return value

    rounded_value = round(value, 2)

    return (
        int(rounded_value)
        if rounded_value.is_integer()
        else float(f"{rounded_value:.2f}")
    )


def get_nested_attr(obj, attr):
    attributes = attr.split(".")
    for attribute in attributes:
        try:
            obj = getattr(obj, attribute)
        except TranslationDoesNotExist:
            obj = str(obj)
    return obj


def get_top_ranking_distinct_risks(data, top_ranking):
    seen_uuids = set()
    distinct = []
    for obj in data:
        array_uuid = [
            obj.service.service.uuid,
            str(obj.asset),
            obj.threat.uuid,
            obj.vulnerability.uuid,
        ]
        combined_uuid = generate_combined_uuid(array_uuid)
        if combined_uuid not in seen_uuids:
            seen_uuids.add(combined_uuid)
            distinct.append(obj)

        if len(distinct) >= top_ranking:
            break
    return distinct


def generate_combined_uuid(array_uuid: List[str]) -> uuid.UUID:
    combined = "".join(str(i_uuid) for i_uuid in array_uuid)
    new_uuid = uuid.uuid3(uuid.NAMESPACE_DNS, combined)

    return str(new_uuid)


def create_entry_log(user, reporting, action):
    log = LogReporting.objects.create(
        user=user,
        reporting=reporting,
        action=action,
    )
    log.save()


def generate_bar_chart(data, labels, is_rate=False):
    fig = go.Figure()
    labels = text_wrap(labels)
    bar_colors_palette = pc.qualitative.Pastel1
    average_colors_palette = pc.qualitative.Set1
    avg_index = 0
    bar_index = 0

    for name, values in data.items():
        if is_rate:
            rate_labels = values["rate_labels"]
            values = values["rate_values"]

        group_name = str(name)[-4:]

        if str(_("average")) in str(name):
            fig.add_trace(
                go.Scatter(
                    x=labels,
                    y=values,
                    name=str(name),
                    mode="markers",
                    marker=dict(
                        size=12,
                        symbol="diamond",
                        color=average_colors_palette[avg_index],
                    ),
                    offsetgroup=group_name,
                    legendgroup=group_name,
                ),
            )
            avg_index += 1

        else:
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=values,
                    name=str(name),
                    marker_color=bar_colors_palette[bar_index],
                    text=rate_labels if is_rate else values,
                    textposition="outside",
                    offsetgroup=group_name,
                    legendgroup=group_name,
                ),
            )
            bar_index += 1

    fig.update_layout(
        hovermode="closest",
        barmode="group",
        scattermode="group",
        bargroupgap=0.2,
        xaxis=dict(
            linecolor="black",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="lightgray",
            linecolor="black",
            rangemode="nonnegative",
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.2,
            xanchor="center",
            yanchor="top",
            traceorder="normal",
            itemwidth=70,
            valign="middle",
        ),
        margin=dict(l=0, r=0, t=0, b=50),
    )

    if is_rate:
        fig.update_layout(yaxis_tickformat=".0%")

    graph = convert_graph_to_base64(fig)

    return graph


def generate_radar_chart(data, labels, levels):
    fig = go.Figure()
    labels = text_wrap(labels)
    line_colors_palette = pc.qualitative.Pastel1
    marker_colors_palette = pc.qualitative.Set1
    index = 0

    for name, values in data.items():
        line_style = "solid"
        line_color = line_colors_palette[index]
        marker_color = marker_colors_palette[index]
        symbol = "circle"

        if str(_("average")) in name:
            line_style = "dash"
            line_color = "#666666"
            marker_color = "#222A2A"
            symbol = "triangle-up"

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                name=str(name),
                fillcolor="rgba(0,0,0,0)",
                marker=dict(
                    symbol=symbol,
                    color=marker_color,
                ),
                mode="lines+markers",
                line=dict(
                    color=line_color,
                    dash=line_style,
                ),
            )
        )
        index += 1

    fig.update_layout(
        polar=dict(
            bgcolor="white",
            gridshape="linear",
            radialaxis=dict(
                range=[0, len(levels) - 1],
                gridcolor="lightgrey",
                angle=90,
                tickangle=90,
            ),
            angularaxis=dict(
                gridcolor="lightgrey",
                tickmode="array",
                linecolor="lightgrey",
                rotation=90,
                direction="clockwise",
            ),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            x=0.5,
            y=-0.1,
            xanchor="center",
            yanchor="top",
            traceorder="normal",
            itemwidth=70,
            valign="middle",
        ),
        margin=dict(l=0, r=0, t=50, b=0),
    )

    graph = convert_graph_to_base64(fig)

    return graph


def generate_colorbar():
    levels = [0, 0.5, 1, 1.5, 2, 2.5, 3]
    labels = [
        "no measure or N/A",
        "",
        "basic",
        "",
        "industry standard",
        "",
        "state of the art",
    ]

    fig = go.Figure(
        data=go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(
                size=0,
                color=[-0.1, 3],
                colorscale=[
                    [0.0, "#F8696B"],
                    [0.17, "#FA9473"],
                    [0.33, "#FCBF7B"],
                    [0.5, "#FFEB84"],
                    [0.67, "#CCDD82"],
                    [0.83, "#98CE7F"],
                    [1.0, "#63BE7B"],
                ],
                colorbar=dict(
                    outlinecolor="#FFFFFF",
                    outlinewidth=0.5,
                    tickvals=levels,
                    ticktext=labels,
                    orientation="h",
                    x=0.5,
                    y=0.5,
                    xanchor="center",
                    thickness=15,
                    ypad=0,
                ),
            ),
        )
    )

    annotations = [
        dict(
            x=0.02,
            y="no measure or N/A",
            text="0",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.19,
            y="",
            text="0.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.35,
            y="basic",
            text="1",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.5,
            y="",
            text="1.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.67,
            y="industry standard",
            text="2",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.83,
            y="",
            text="2.5",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
        dict(
            x=0.98,
            y="state of the art",
            text="3",
            showarrow=False,
            xref="paper",
            yref="paper",
            xanchor="center",
        ),
    ]

    fig.update_layout(annotations=annotations)

    fig.update_layout(
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=200, b=15),
        height=50,
    )

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)

    graph = convert_graph_to_base64(fig, "png")

    return graph


def text_wrap(text, max_line_length=20):
    if isinstance(text, list):
        text_wrapped = [
            "<br>".join(textwrap.wrap(label, width=max_line_length)) for label in text
        ]
    elif isinstance(text, str):
        text_wrapped = "<br>".join(textwrap.wrap(text, width=max_line_length))
    else:
        return None
    return text_wrapped


def convert_graph_to_base64(fig, export_format="svg"):
    buffer = BytesIO()
    fig.write_image(buffer, format=export_format, engine="kaleido", scale=3)
    buffer.seek(0)
    image_svg = buffer.getvalue()
    buffer.close()

    graph = base64.b64encode(image_svg)
    graph = graph.decode("utf-8")

    return graph
