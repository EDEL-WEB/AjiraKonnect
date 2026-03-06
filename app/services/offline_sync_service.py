from app import db
from app.models.offline import SyncQueue
from app.models import Job, User
from datetime import datetime

class OfflineSyncService:
    
    @staticmethod
    def queue_offline_action(user_id, device_id, action_type, payload, client_timestamp):
        # Queue offline action
        sync_item = SyncQueue(
            user_id=user_id,
            device_id=device_id,
            action_type=action_type,
            payload=payload,
            client_timestamp=client_timestamp
        )
        db.session.add(sync_item)
        db.session.commit()
        
        # If action is job update, create update record
        if action_type in ['update_progress', 'add_note', 'upload_photo']:
            from app.models.job_update import JobUpdate
            update = JobUpdate(
                job_id=payload.get('job_id'),
                user_id=user_id,
                update_type=action_type.replace('update_', '').replace('add_', '').replace('upload_', ''),
                progress_percentage=payload.get('progress_percentage'),
                note=payload.get('note'),
                photo_urls=payload.get('photo_urls'),
                created_offline=True
            )
            db.session.add(update)
            db.session.commit()
        
        return sync_item.id
    
    @staticmethod
    def process_sync_queue(user_id, batch_size=50):
        pending_items = SyncQueue.query.filter_by(
            user_id=user_id,
            status='pending'
        ).order_by(SyncQueue.client_timestamp).limit(batch_size).all()
        
        results = []
        
        for item in pending_items:
            try:
                item.status = 'processing'
                db.session.commit()
                
                if item.action_type == 'create_job':
                    result = OfflineSyncService._sync_create_job(item)
                elif item.action_type == 'update_job':
                    result = OfflineSyncService._sync_update_job(item)
                elif item.action_type == 'add_note':
                    result = OfflineSyncService._sync_add_note(item)
                else:
                    result = {'success': False, 'error': 'Unknown action'}
                
                if result['success']:
                    item.status = 'completed'
                    item.processed_at = datetime.utcnow()
                else:
                    item.status = 'failed'
                    item.error_message = result.get('error')
                    item.retry_count += 1
                
                results.append({'id': item.id, 'success': result['success']})
                
            except Exception as e:
                item.status = 'failed'
                item.error_message = str(e)
                item.retry_count += 1
                results.append({'id': item.id, 'success': False, 'error': str(e)})
            
            db.session.commit()
        
        return results
    
    @staticmethod
    def _sync_create_job(sync_item):
        payload = sync_item.payload
        user = User.query.get(sync_item.user_id)
        
        if not user or user.role != 'customer':
            return {'success': False, 'error': 'Invalid user'}
        
        existing = Job.query.filter(
            Job.customer_id == sync_item.user_id,
            Job.title == payload.get('title'),
            Job.created_at >= sync_item.client_timestamp
        ).first()
        
        if existing:
            return {'success': True, 'job_id': existing.id, 'note': 'Duplicate prevented'}
        
        from app.services.job_service import JobService
        job = JobService.create_job(
            customer_id=sync_item.user_id,
            category_id=payload['category_id'],
            title=payload['title'],
            description=payload['description'],
            location=payload['location'],
            budget=payload['budget']
        )
        
        return {'success': True, 'job_id': job.id}
    
    @staticmethod
    def _sync_update_job(sync_item):
        payload = sync_item.payload
        job = Job.query.get(payload.get('job_id'))
        
        if not job:
            return {'success': False, 'error': 'Job not found'}
        
        if job.updated_at > sync_item.client_timestamp:
            return {'success': True, 'note': 'Stale update ignored'}
        
        from app.services.job_service import JobService
        try:
            JobService.update_job_status(payload.get('job_id'), payload.get('status'))
            return {'success': True}
        except ValueError as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _sync_add_note(sync_item):
        payload = sync_item.payload
        job = Job.query.get(payload.get('job_id'))
        
        if not job:
            return {'success': False, 'error': 'Job not found'}
        
        job.description += f"\n[Note]: {payload.get('note')}"
        db.session.commit()
        
        return {'success': True}
    
    @staticmethod
    def get_pending_count(user_id):
        return SyncQueue.query.filter_by(user_id=user_id, status='pending').count()
