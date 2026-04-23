from app import db
from app.models import Payment, Wallet, Transaction, Job
from app.models.worker import Worker
from datetime import datetime
from flask import current_app


class EscrowService:

    # ── Step 1: Pre-authorize on job creation ─────────────────────────────────

    @staticmethod
    def pre_authorize(job_id, customer_id):
        """
        Reserve funds when customer creates a job.
        No money moves yet — just calculates and records the intent.
        """
        job = Job.query.get_or_404(job_id)

        if Payment.query.filter_by(job_id=job_id).first():
            raise ValueError('Payment already exists for this job')

        commission_rate = current_app.config['COMMISSION_RATE']
        amount          = float(job.budget)
        commission      = round(amount * commission_rate, 2)
        worker_payout   = round(amount - commission, 2)

        payment = Payment(
            job_id        = job_id,
            amount        = amount,
            commission    = commission,
            worker_payout = worker_payout,
            status        = 'pre_authorized'
        )
        db.session.add(payment)
        db.session.commit()
        return payment

    # ── Step 2: Hold funds when worker accepts ────────────────────────────────

    @staticmethod
    def hold_payment(job_id):
        """
        Debit customer wallet and lock funds in escrow when worker accepts.
        Uses SELECT FOR UPDATE to prevent race conditions.
        """
        payment = Payment.query.filter_by(job_id=job_id).first_or_404()

        if payment.status != 'pre_authorized':
            raise ValueError(f'Cannot hold payment with status: {payment.status}')

        job = Job.query.get(job_id)
        customer_wallet = Wallet.query.filter_by(
            user_id=job.customer_id
        ).with_for_update().first()

        if not customer_wallet:
            raise ValueError('Customer wallet not found')

        if float(customer_wallet.balance) < float(payment.amount):
            raise ValueError(
                f'Insufficient balance. Need KES {payment.amount}, '
                f'have KES {customer_wallet.balance}'
            )

        # Debit customer
        customer_wallet.balance -= payment.amount

        db.session.add(Transaction(
            wallet_id   = customer_wallet.id,
            payment_id  = payment.id,
            type        = 'debit',
            amount      = payment.amount,
            description = f'Escrow hold for job: {job.title}',
            balance_after = customer_wallet.balance
        ))

        payment.status  = 'held'
        payment.paid_at = datetime.utcnow()
        db.session.commit()
        return payment

    # ── Step 3: Release to worker on customer approval ────────────────────────

    @staticmethod
    def release_payment(job_id, customer_id):
        """
        Credit worker wallet with payout (budget minus 15% commission).
        Only callable by the customer who owns the job.
        """
        payment = Payment.query.filter_by(job_id=job_id).first_or_404()

        if payment.status != 'held':
            raise ValueError(f'Cannot release payment with status: {payment.status}')

        job = Job.query.get(job_id)

        if job.customer_id != customer_id:
            raise ValueError('Only the job customer can release payment')

        if job.status != 'completed':
            raise ValueError('Job must be completed before releasing payment')

        worker_wallet = Wallet.query.filter_by(
            user_id=job.worker.user_id
        ).with_for_update().first()

        if not worker_wallet:
            raise ValueError('Worker wallet not found')

        worker_wallet.balance += payment.worker_payout

        db.session.add(Transaction(
            wallet_id   = worker_wallet.id,
            payment_id  = payment.id,
            type        = 'credit',
            amount      = payment.worker_payout,
            description = f'Payment for job: {job.title} (after 15% commission)',
            balance_after = worker_wallet.balance
        ))

        payment.status      = 'released'
        payment.released_at = datetime.utcnow()
        db.session.commit()

        # Notify worker
        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_payment_released(job, payment.worker_payout)
        except Exception:
            pass

        return payment

    # ── Step 4: Refund to customer (cancel / pre-completion) ──────────────────

    @staticmethod
    def refund_payment(job_id, requester_id, requester_role):
        """
        Refund full amount to customer.
        Customer can refund if payment is pre_authorized or held (job not completed).
        Admin can refund at any held/disputed stage.
        """
        payment = Payment.query.filter_by(job_id=job_id).first_or_404()
        job     = Job.query.get(job_id)

        if requester_role == 'customer':
            if job.customer_id != requester_id:
                raise ValueError('Only the job customer can request a refund')
            if payment.status not in ('pre_authorized', 'held'):
                raise ValueError(f'Cannot refund payment with status: {payment.status}')
            if job.status == 'completed':
                raise ValueError('Cannot refund a completed job — raise a dispute instead')

        elif requester_role == 'admin':
            if payment.status not in ('held', 'disputed'):
                raise ValueError(f'Cannot refund payment with status: {payment.status}')
        else:
            raise ValueError('Insufficient permissions to refund')

        # Only credit back if funds were actually debited
        if payment.status in ('held', 'disputed'):
            customer_wallet = Wallet.query.filter_by(
                user_id=job.customer_id
            ).with_for_update().first()

            customer_wallet.balance += payment.amount

            db.session.add(Transaction(
                wallet_id   = customer_wallet.id,
                payment_id  = payment.id,
                type        = 'credit',
                amount      = payment.amount,
                description = f'Refund for job: {job.title}',
                balance_after = customer_wallet.balance
            ))

        payment.status = 'refunded'
        job.status     = 'cancelled'
        db.session.commit()
        return payment

    # ── Step 5: Raise dispute ─────────────────────────────────────────────────

    @staticmethod
    def raise_dispute(job_id, customer_id, reason):
        """Customer raises a dispute on a completed job before releasing payment."""
        payment = Payment.query.filter_by(job_id=job_id).first_or_404()
        job     = Job.query.get(job_id)

        if job.customer_id != customer_id:
            raise ValueError('Only the job customer can raise a dispute')

        if payment.status != 'held':
            raise ValueError(f'Cannot dispute payment with status: {payment.status}')

        if job.status != 'completed':
            raise ValueError('Can only dispute a completed job')

        payment.status         = 'disputed'
        payment.dispute_reason = reason
        job.status             = 'disputed'
        db.session.commit()
        return payment

    # ── Step 6: Admin resolves dispute ────────────────────────────────────────

    @staticmethod
    def resolve_dispute(job_id, refund_percentage, resolution_note):
        """
        Admin splits payment between customer and worker.
        refund_percentage=0   → full payment to worker
        refund_percentage=100 → full refund to customer
        refund_percentage=50  → 50/50 split
        """
        payment = Payment.query.filter_by(job_id=job_id).first_or_404()
        job     = Job.query.get(job_id)

        if payment.status != 'disputed':
            raise ValueError('Payment is not in disputed state')

        if not (0 <= refund_percentage <= 100):
            raise ValueError('refund_percentage must be between 0 and 100')

        total          = float(payment.amount)
        refund_amount  = round(total * refund_percentage / 100, 2)
        payout_amount  = round(total - refund_amount, 2)
        # recalculate commission only on what worker actually receives
        commission     = round(payout_amount * float(current_app.config['COMMISSION_RATE']), 2)
        net_payout     = round(payout_amount - commission, 2)

        # Refund portion to customer
        if refund_amount > 0:
            customer_wallet = Wallet.query.filter_by(
                user_id=job.customer_id
            ).with_for_update().first()
            customer_wallet.balance += refund_amount
            db.session.add(Transaction(
                wallet_id   = customer_wallet.id,
                payment_id  = payment.id,
                type        = 'credit',
                amount      = refund_amount,
                description = f'Dispute refund ({refund_percentage}%) for job: {job.title}',
                balance_after = customer_wallet.balance
            ))

        # Pay portion to worker
        if net_payout > 0:
            worker_wallet = Wallet.query.filter_by(
                user_id=job.worker.user_id
            ).with_for_update().first()
            worker_wallet.balance += net_payout
            db.session.add(Transaction(
                wallet_id   = worker_wallet.id,
                payment_id  = payment.id,
                type        = 'credit',
                amount      = net_payout,
                description = f'Dispute payout ({100 - refund_percentage}%) for job: {job.title}',
                balance_after = worker_wallet.balance
            ))

        payment.status          = 'released'
        payment.worker_payout   = net_payout
        payment.commission      = commission
        payment.resolution_note = resolution_note
        payment.released_at     = datetime.utcnow()
        job.status              = 'completed'
        db.session.commit()
        return payment, refund_amount, net_payout

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_escrow_status(job_id):
        """Return full escrow snapshot for a job."""
        job     = Job.query.get_or_404(job_id)
        payment = Payment.query.filter_by(job_id=job_id).first()

        return {
            'job_id':         job.id,
            'job_title':      job.title,
            'job_status':     job.status,
            'budget':         str(job.budget),
            'escrow_status':  payment.status if payment else 'none',
            'amount':         str(payment.amount)        if payment else None,
            'commission':     str(payment.commission)    if payment else None,
            'worker_payout':  str(payment.worker_payout) if payment else None,
            'paid_at':        payment.paid_at.isoformat()     if payment and payment.paid_at     else None,
            'released_at':    payment.released_at.isoformat() if payment and payment.released_at else None,
            'dispute_reason': payment.dispute_reason          if payment else None,
        }
