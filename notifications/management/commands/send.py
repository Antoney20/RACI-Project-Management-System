"""
Management command to manually trigger notifications

Usage:
    python manage.py send_notifications
    python manage.py send_notifications --type leaves
    python manage.py send_notifications --type activities
    python manage.py send_notifications --type reviews
    python manage.py send_notifications --type contracts
    python manage.py send_notifications --send-pending
"""
from django.core.management.base import BaseCommand

from notifications.service import NotificationService



class Command(BaseCommand):
    help = 'Send notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['leaves', 'activities', 'reviews', 'contracts', 'all'],
            default='all',
            help='Type of notifications to send'
        )
        parser.add_argument(
            '--send-pending',
            action='store_true',
            help='Send all pending notifications via email'
        )
    
    def handle(self, *args, **options):
        notification_type = options['type']
        
        results = {}
        
        if notification_type in ['leaves', 'all']:
            self.stdout.write('Checking pending leave approvals...')
            results['leaves'] = NotificationService.notify_pending_leave_approvals()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Created {results['leaves']['created']} leave notifications"
            ))
        
        if notification_type in ['activities', 'all']:
            self.stdout.write('Checking activities due soon...')
            results['activities_due'] = NotificationService.notify_activity_due_soon()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Created {results['activities_due']['created']} due activity notifications"
            ))
            
            self.stdout.write('Checking overdue activities...')
            results['activities_overdue'] = NotificationService.notify_overdue_activities()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Created {results['activities_overdue']['created']} overdue activity notifications"
            ))
        
        if notification_type in ['reviews', 'all']:
            self.stdout.write('Checking pending reviews...')
            results['reviews'] = NotificationService.notify_pending_reviews()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Created {results['reviews']['created']} review notifications"
            ))
        
        if notification_type in ['contracts', 'all']:
            self.stdout.write('Checking expiring contracts...')
            results['contracts'] = NotificationService.notify_expiring_contracts()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Created {results['contracts']['created']} contract notifications"
            ))
        
        # Send pending notifications if requested
        if options['send_pending']:
            self.stdout.write('Sending pending notifications...')
            send_results = NotificationService.send_pending_notifications()
            self.stdout.write(self.style.SUCCESS(
                f"✓ Sent {send_results['sent']} notifications"
            ))
            if send_results['failed'] > 0:
                self.stdout.write(self.style.WARNING(
                    f"⚠ {send_results['failed']} notifications failed to send"
                ))
        
        total_created = sum(r.get('created', 0) for r in results.values())
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Total: {total_created} notifications created"
        ))
