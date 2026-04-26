from app import db
from app.models.offline import USSDSession
from app.models import User, Job, Category, Worker
from app.models.payment import Wallet, Transaction


class USSDService:

    @staticmethod
    def handle_ussd_request(session_id, phone, text):
        session = USSDSession.query.filter_by(session_id=session_id).first()
        if not session:
            session = USSDSession(session_id=session_id, phone=phone, context_data={})
            db.session.add(session)

        if session.context_data is None:
            session.context_data = {}

        user = User.query.filter_by(phone=phone).first()
        if user and not session.user_id:
            session.user_id = user.id

        text_array = text.split('*') if text else []

        if text == '':
            response = USSDService._main_menu(session, user)
        elif session.state == 'main_menu':
            response = USSDService._handle_main_menu(session, user, text_array[0])

        # ── Customer states ───────────────────────────────────────────────────
        elif session.state == 'select_category':
            response = USSDService._handle_category_selection(session, user, text_array[-1])
        elif session.state == 'enter_location':
            response = USSDService._handle_location_input(session, user, text_array[-1])
        elif session.state == 'enter_budget':
            response = USSDService._handle_budget_input(session, user, text_array[-1])
        elif session.state == 'release_payment':
            response = USSDService._handle_release_payment(session, user, text_array[-1])
        elif session.state == 'cancel_job':
            response = USSDService._handle_cancel_job(session, user, text_array[-1])
        elif session.state == 'rate_worker_select':
            response = USSDService._handle_rate_worker_select(session, user, text_array[-1])
        elif session.state == 'rate_worker_score':
            response = USSDService._handle_rate_worker_score(session, user, text_array[-1])
        elif session.state == 'approve_rate_select':
            response = USSDService._handle_approve_rate_select(session, user, text_array[-1])
        elif session.state == 'approve_rate_confirm':
            response = USSDService._handle_approve_rate_confirm(session, user, text_array[-1])

        # ── Worker states ─────────────────────────────────────────────────────
        elif session.state == 'accept_job':
            response = USSDService._handle_accept_job_select(session, user, text_array[-1])
        elif session.state == 'enter_proposed_rate':
            response = USSDService._handle_proposed_rate(session, user, text_array[-1])
        elif session.state == 'view_job_detail':
            response = USSDService._handle_worker_job_detail(session, user, text_array[-1])
        elif session.state == 'update_status':
            response = USSDService._handle_status_update(session, user, text_array[-1])

        else:
            response = 'END Invalid session.'

        db.session.commit()
        return response

    # ── Main Menus ────────────────────────────────────────────────────────────

    @staticmethod
    def _main_menu(session, user):
        session.state = 'main_menu'
        if not user:
            return 'END Register on KaziConnect app first.'

        if user.role == 'customer':
            return (
                'CON KaziConnect - Customer\n'
                '1. Book a Service\n'
                '2. My Jobs\n'
                '3. Approve Worker Rate\n'
                '4. Release Payment\n'
                '5. Cancel Job\n'
                '6. Rate a Worker\n'
                '7. Wallet Balance\n'
                '8. Transaction History'
            )
        else:
            return (
                'CON KaziConnect - Worker\n'
                '1. Available Jobs\n'
                '2. Accept a Job\n'
                '3. My Active Jobs\n'
                '4. Update Job Status\n'
                '5. Completed Jobs\n'
                '6. Wallet Balance\n'
                '7. Transaction History'
            )

    @staticmethod
    def _handle_main_menu(session, user, choice):
        if user.role == 'customer':
            if choice == '1':
                session.state = 'select_category'
                return USSDService._show_categories()
            elif choice == '2':
                return USSDService._show_customer_jobs(user)
            elif choice == '3':
                return USSDService._show_pending_rate_approvals(session, user)
            elif choice == '4':
                return USSDService._show_releasable_jobs(session, user)
            elif choice == '5':
                return USSDService._show_cancellable_jobs(session, user)
            elif choice == '6':
                return USSDService._show_rateable_jobs(session, user)
            elif choice == '7':
                return USSDService._show_wallet(user)
            elif choice == '8':
                return USSDService._show_transactions(user)

        elif user.role == 'worker':
            worker = Worker.query.filter_by(user_id=user.id).first()
            if not worker:
                return 'END Worker profile not found.'
            if choice == '1':
                return USSDService._show_available_jobs(worker)
            elif choice == '2':
                return USSDService._show_available_jobs_to_accept(session, worker)
            elif choice == '3':
                return USSDService._show_worker_active_jobs(session, worker)
            elif choice == '4':
                return USSDService._show_worker_active_jobs(session, worker, for_update=True)
            elif choice == '5':
                return USSDService._show_worker_completed_jobs(worker)
            elif choice == '6':
                return USSDService._show_wallet(user)
            elif choice == '7':
                return USSDService._show_transactions(user)

        return 'END Invalid option.'

    # ── Customer: Book Service ────────────────────────────────────────────────

    @staticmethod
    def _show_categories():
        categories = Category.query.filter_by(is_active=True).limit(7).all()
        response = 'CON Select Category:\n'
        for idx, cat in enumerate(categories, 1):
            response += f'{idx}. {cat.name}\n'
        return response

    @staticmethod
    def _handle_category_selection(session, user, choice):
        categories = Category.query.filter_by(is_active=True).limit(7).all()
        try:
            selected = categories[int(choice) - 1]
            session.context_data = {**session.context_data, 'category_id': selected.id}
            session.state = 'enter_location'
            return 'CON Enter your location:'
        except (IndexError, ValueError):
            return 'END Invalid selection.'

    @staticmethod
    def _handle_location_input(session, user, location):
        session.context_data = {**session.context_data, 'location': location}
        session.state = 'enter_budget'
        return 'CON Enter budget (KES):'

    @staticmethod
    def _handle_budget_input(session, user, budget):
        try:
            from app.services.job_service import JobService
            job = JobService.create_job(
                customer_id=user.id,
                category_id=session.context_data['category_id'],
                title='USSD Job Request',
                description='Created via USSD',
                location=session.context_data['location'],
                budget=float(budget)
            )
            session.is_active = False
            return f'END Job posted! Ref: {job.id[:8]}.\nWorkers will be notified via SMS.'
        except ValueError:
            return 'END Invalid budget. Please enter a number.'
        except Exception as e:
            return f'END Failed: {str(e)[:60]}'

    # ── Customer: Approve Worker Rate ─────────────────────────────────────────

    @staticmethod
    def _show_pending_rate_approvals(session, user):
        jobs = Job.query.filter(
            Job.customer_id == user.id,
            Job.rate_status == 'pending_approval'
        ).order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No pending rate approvals.'
        session.state = 'approve_rate_select'
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in jobs]}
        response = 'CON Pending Rate Approvals:\n'
        for idx, job in enumerate(jobs, 1):
            response += f'{idx}. {job.title[:15]} KES {job.proposed_rate}\n'
        return response

    @staticmethod
    def _handle_approve_rate_select(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job = Job.query.get(job_ids[int(choice) - 1])
            session.context_data = {**session.context_data, 'selected_job_id': job.id}
            session.state = 'approve_rate_confirm'
            return (
                f'CON {job.title[:20]}\n'
                f'Worker rate: KES {job.proposed_rate}\n'
                f'Location: {job.location[:20]}\n'
                f'1. Approve\n'
                f'2. Reject'
            )
        except (IndexError, TypeError, ValueError):
            return 'END Invalid selection.'

    @staticmethod
    def _handle_approve_rate_confirm(session, user, choice):
        try:
            job_id = session.context_data.get('selected_job_id')
            if choice not in ('1', '2'):
                return 'END Invalid option. Dial again.'
            approved = choice == '1'
            from app.services.job_service import JobService
            JobService.approve_rate(job_id, user.id, approved)
            session.is_active = False
            if approved:
                job = Job.query.get(job_id)
                return f'END Rate approved! KES {job.budget} held in escrow.\nWorker notified via SMS.'
            return 'END Rate rejected. Job cancelled.\nWorker notified via SMS.'
        except ValueError as e:
            return f'END {str(e)}'
        except Exception:
            return 'END Failed. Please try again.'

    # ── Customer: My Jobs ─────────────────────────────────────────────────────

    @staticmethod
    def _show_customer_jobs(user):
        jobs = Job.query.filter_by(customer_id=user.id).order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END You have no jobs yet.'
        response = 'END Your Recent Jobs:\n'
        for job in jobs:
            response += f'{job.title[:15]} - {job.status}\n'
        return response

    # ── Customer: Release Payment ─────────────────────────────────────────────

    @staticmethod
    def _show_releasable_jobs(session, user):
        from app.models.payment import Payment
        jobs = Job.query.filter_by(customer_id=user.id, status='completed').all()
        releasable = [j for j in jobs if Payment.query.filter_by(job_id=j.id, status='held').first()]
        if not releasable:
            return 'END No completed jobs pending payment release.'
        session.state = 'release_payment'
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in releasable]}
        response = 'CON Select job to release payment:\n'
        for idx, job in enumerate(releasable, 1):
            response += f'{idx}. {job.title[:15]} - KES {job.budget}\n'
        return response

    @staticmethod
    def _handle_release_payment(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job_id = job_ids[int(choice) - 1]
            from app.services.escrow_service import EscrowService
            EscrowService.release_payment(job_id, user.id)
            session.is_active = False
            return 'END Payment released to worker successfully.\nThey will be notified via SMS.'
        except ValueError as e:
            return f'END {str(e)}'
        except (IndexError, TypeError):
            return 'END Invalid selection.'

    # ── Customer: Cancel Job ──────────────────────────────────────────────────

    @staticmethod
    def _show_cancellable_jobs(session, user):
        jobs = Job.query.filter(
            Job.customer_id == user.id,
            Job.status.in_(['pending', 'accepted'])
        ).order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No cancellable jobs.'
        session.state = 'cancel_job'
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in jobs]}
        response = 'CON Select job to cancel:\n'
        for idx, job in enumerate(jobs, 1):
            response += f'{idx}. {job.title[:15]} ({job.status})\n'
        return response

    @staticmethod
    def _handle_cancel_job(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job = Job.query.get(job_ids[int(choice) - 1])
            from app.services.escrow_service import EscrowService
            from app.models.payment import Payment
            payment = Payment.query.filter_by(job_id=job.id).first()
            if payment and payment.status in ('pre_authorized', 'held'):
                EscrowService.refund_payment(job.id, user.id, 'customer')
            else:
                job.status = 'cancelled'
                db.session.commit()
            session.is_active = False
            return 'END Job cancelled successfully.'
        except ValueError as e:
            return f'END {str(e)}'
        except (IndexError, TypeError):
            return 'END Invalid selection.'

    # ── Customer: Rate Worker ─────────────────────────────────────────────────

    @staticmethod
    def _show_rateable_jobs(session, user):
        jobs = Job.query.filter_by(customer_id=user.id, status='completed').order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No completed jobs to rate.'
        session.state = 'rate_worker_select'
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in jobs]}
        response = 'CON Select job to rate worker:\n'
        for idx, job in enumerate(jobs, 1):
            response += f'{idx}. {job.title[:20]}\n'
        return response

    @staticmethod
    def _handle_rate_worker_select(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job_id = job_ids[int(choice) - 1]
            session.context_data = {**session.context_data, 'rate_job_id': job_id}
            session.state = 'rate_worker_score'
            return 'CON Rate the worker (1-5):\n1. Poor\n2. Fair\n3. Good\n4. Very Good\n5. Excellent'
        except (IndexError, ValueError):
            return 'END Invalid selection.'

    @staticmethod
    def _handle_rate_worker_score(session, user, choice):
        try:
            rating = int(choice)
            if rating not in range(1, 6):
                return 'END Rating must be between 1 and 5.'
            job_id = session.context_data.get('rate_job_id')
            job = Job.query.get(job_id)
            from app.models import Review
            existing = Review.query.filter_by(job_id=job_id, customer_id=user.id).first()
            if existing:
                return 'END You already rated this job.'
            from app.services.review_service import ReviewService
            ReviewService.create_review(
                job_id=job_id,
                customer_id=user.id,
                worker_id=job.worker_id,
                rating=rating,
                comment='Rated via USSD'
            )
            session.is_active = False
            return f'END Thank you! Worker rated {rating}/5.'
        except ValueError:
            return 'END Invalid rating.'
        except Exception as e:
            return f'END Failed: {str(e)[:60]}'

    # ── Worker: Available Jobs ────────────────────────────────────────────────

    @staticmethod
    def _show_available_jobs(worker):
        jobs = Job.query.filter_by(status='pending').order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No available jobs right now.'
        response = 'END Available Jobs:\n'
        for job in jobs:
            response += f'{job.title[:15]} KES{job.budget} {job.location[:8]}\n'
        return response

    @staticmethod
    def _show_available_jobs_to_accept(session, worker):
        jobs = Job.query.filter_by(status='pending').order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No available jobs to accept.'
        session.state = 'accept_job'
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in jobs]}
        response = 'CON Select job to accept:\n'
        for idx, job in enumerate(jobs, 1):
            loc = job.location[:8]
            response += f'{idx}. {job.title[:15]} {loc}\n'
        return response

    @staticmethod
    def _handle_accept_job_select(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job = Job.query.get(job_ids[int(choice) - 1])
            session.context_data = {**session.context_data, 'selected_job_id': job.id}
            session.state = 'enter_proposed_rate'
            return (
                f'CON Job: {job.title[:20]}\n'
                f'Location: {job.location[:20]}\n'
                f'Enter your rate (KES):'
            )
        except (IndexError, TypeError, ValueError):
            return 'END Invalid selection.'

    @staticmethod
    def _handle_proposed_rate(session, user, rate):
        try:
            proposed_rate = float(rate)
            if proposed_rate <= 0:
                return 'END Rate must be greater than 0.'
            job_id = session.context_data.get('selected_job_id')
            worker = Worker.query.filter_by(user_id=user.id).first()
            from app.services.job_service import JobService
            job = JobService.accept_job(job_id, worker.id, proposed_rate)
            session.is_active = False
            return (
                f'END Rate of KES {proposed_rate} proposed!\n'
                f'Ref: {job.id[:8]}\n'
                f'Customer will be notified to approve via SMS.'
            )
        except ValueError as e:
            return f'END {str(e)}'
        except Exception:
            return 'END Failed to propose rate. Try again.'

    # ── Worker: Active Jobs ───────────────────────────────────────────────────

    @staticmethod
    def _show_worker_active_jobs(session, worker, for_update=False):
        jobs = Job.query.filter(
            Job.worker_id == worker.id,
            Job.status.in_(['accepted', 'in_progress'])
        ).order_by(Job.created_at.desc()).limit(5).all()
        if not jobs:
            return 'END No active jobs.'
        state = 'update_status' if for_update else 'view_job_detail'
        session.state = state
        session.context_data = {**session.context_data, 'job_ids': [j.id for j in jobs]}
        response = 'CON Select Job:\n'
        for idx, job in enumerate(jobs, 1):
            response += f'{idx}. {job.title[:15]} ({job.status})\n'
        return response

    @staticmethod
    def _handle_worker_job_detail(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job = Job.query.get(job_ids[int(choice) - 1])
            return (
                f'END Job: {job.title}\n'
                f'Status: {job.status}\n'
                f'Budget: KES {job.budget}\n'
                f'Location: {job.location}'
            )
        except (IndexError, ValueError):
            return 'END Invalid selection.'

    @staticmethod
    def _handle_status_update(session, user, choice):
        try:
            job_ids = session.context_data.get('job_ids', [])
            job = Job.query.get(job_ids[int(choice) - 1])
            next_status = {'accepted': 'in_progress', 'in_progress': 'completed'}.get(job.status)
            if not next_status:
                return f'END Cannot update job with status: {job.status}'
            from app.services.job_service import JobService
            JobService.update_job_status(job.id, next_status)
            session.is_active = False
            return f'END Job updated to {next_status.upper()}.\nCustomer notified via SMS.'
        except ValueError as e:
            return f'END {str(e)}'
        except (IndexError, TypeError):
            return 'END Invalid selection.'

    # ── Worker: Completed Jobs ────────────────────────────────────────────────

    @staticmethod
    def _show_worker_completed_jobs(worker):
        jobs = Job.query.filter_by(worker_id=worker.id, status='completed').order_by(Job.completed_at.desc()).limit(5).all()
        if not jobs:
            return 'END No completed jobs yet.'
        response = 'END Completed Jobs:\n'
        for job in jobs:
            date = job.completed_at.strftime('%d/%m') if job.completed_at else 'N/A'
            response += f'{job.title[:15]} KES{job.budget} {date}\n'
        return response

    # ── Shared: Wallet & Transactions ─────────────────────────────────────────

    @staticmethod
    def _show_wallet(user):
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        if not wallet:
            return 'END Wallet not found.'
        return (
            f'END KaziConnect Wallet\n'
            f'Balance: KES {wallet.balance}\n'
            f'Dial again to refresh.'
        )

    @staticmethod
    def _show_transactions(user):
        wallet = Wallet.query.filter_by(user_id=user.id).first()
        if not wallet:
            return 'END Wallet not found.'
        txns = Transaction.query.filter_by(wallet_id=wallet.id).order_by(Transaction.created_at.desc()).limit(5).all()
        if not txns:
            return 'END No transactions yet.'
        response = 'END Recent Transactions:\n'
        for t in txns:
            sign = '+' if t.type == 'credit' else '-'
            date = t.created_at.strftime('%d/%m')
            response += f'{sign}KES{t.amount} {date}\n'
        return response
