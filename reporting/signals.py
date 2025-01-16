from django.db.models.signals import pre_delete, post_delete
from django.dispatch import receiver

from .models import RiskData


@receiver(pre_delete, sender=RiskData)
def cache_related_recommendationdata(sender, instance, **kwargs):
    # Attach related RecommendationData instances to the instance for later use
    instance._cached_recommendation_data = list(instance.recommendations.all())


@receiver(post_delete, sender=RiskData)
def delete_orphaned_recommendationdata(sender, instance, **kwargs):
    # Retrieve cached recommendationdata instances
    related_bs = getattr(instance, "_cached_recommendation_data", [])
    print(instance)
    print(related_bs)

    # Check if reco are linked to another riskdata
    for b in related_bs:
        if b.riskdata_set.count() == 0:
            b.delete()
