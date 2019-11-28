# -*- coding: UTF-8 -*-
from django.dispatch import receiver
from dns_pod.signals.signals import post_update, post_save, post_delete
from dns_pod.models import Zone, Record


@receiver(post_update, dispatch_uid="post_update_receiver")
def post_update_receiver(sender, **kwargs):
    print(kwargs['user'])
    print('my_signal received')


@receiver(post_save, dispatch_uid="post_save_receiver")
def post_save_receiver(sender, created, instance, **kwargs):
    dns_type = Zone.objects.get(domain_name=instance.zone)
    if created:
        # True if a new record was created.
        Record().using().save()
    print('my_signal received')


@receiver(post_delete, dispatch_uid="post_delete_receiver")
def post_delete_receiver(sender, created, instance, **kwargs):
    print(kwargs['user'])
    print('my_signal received')



