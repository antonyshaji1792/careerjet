from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.contact import ContactThread, ContactMessage
from app.extensions import db

bp = Blueprint('contact', __name__, url_prefix='/contact')

@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message_content = request.form.get('message')
        
        if not subject or not message_content:
            flash('Subject and message are required.', 'danger')
            return redirect(url_for('contact.index'))
            
        thread = ContactThread(
            user_id=current_user.id if current_user.is_authenticated else None,
            guest_name=name if not current_user.is_authenticated else None,
            guest_email=email if not current_user.is_authenticated else None,
            subject=subject
        )
        db.session.add(thread)
        db.session.flush() # To get thread ID
        
        message = ContactMessage(
            thread_id=thread.id,
            sender_id=current_user.id if current_user.is_authenticated else None,
            is_admin=False,
            content=message_content
        )
        db.session.add(message)
        db.session.commit()
        
        flash('Your message has been sent. We will get back to you soon!', 'success')
        return redirect(url_for('contact.index'))
        
    return render_template('contact/index.html')

@bp.route('/my-requests', methods=['GET'])
@login_required
def my_requests():
    threads = ContactThread.query.filter_by(user_id=current_user.id).order_by(ContactThread.updated_at.desc()).all()
    return render_template('contact/my_requests.html', threads=threads)

@bp.route('/thread/<int:thread_id>', methods=['GET', 'POST'])
@login_required
def view_thread(thread_id):
    thread = ContactThread.query.get_or_404(thread_id)
    if thread.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('main.index'))
        
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            message = ContactMessage(
                thread_id=thread.id,
                sender_id=current_user.id,
                is_admin=False,
                content=content
            )
            thread.status = 'open'
            db.session.add(message)
            db.session.commit()
            flash('Reply sent.', 'success')
            return redirect(url_for('contact.view_thread', thread_id=thread_id))
            
    return render_template('contact/view_thread.html', thread=thread)
