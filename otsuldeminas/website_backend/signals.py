from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cidade


@receiver(post_save, sender=Cidade)
def collect_indicators_for_new_city(sender, instance, created, **kwargs):
  if not created or not instance.ibge_code:
    return

  def enqueue_collection():
    from etl.tasks import task_coletar_indicadores_ibge

    task_coletar_indicadores_ibge.delay(instance.pk)

  transaction.on_commit(enqueue_collection)