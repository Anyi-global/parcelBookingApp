from app import create_app, mongo, mail
from flask import Blueprint, render_template, url_for, flash, redirect, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_mail import Message
from flask_bcrypt import Bcrypt
from app.models import User
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
import secrets
import os
import datetime
from bson.objectid import ObjectId
from functools import wraps


# Initialize the Blueprint
bp = Blueprint('admin', __name__)

# Initialize extensions
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'

# User loader
@login_manager.user_loader
def load_user(user_id):
    return mongo.db.users.find_one({'_id': ObjectId(user_id)})

def nigerian_time():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    today = datetime.date.today()
    d2 = today.strftime("%B %d, %Y")
    tm = now.strftime("%H:%M:%S %p")
    return (d2 +' '+'at'+' '+tm)

# Email utility functions
def send_email(subject, recipient, body):
    msg = Message(subject, sender=os.getenv('MAIL_USERNAME'), recipients=[recipient])
    msg.body = body
    mail.send(msg)

def send_parcel_received_email(parcel):
    subject = "Parcel Received"
    recipient = parcel['sender_email']
    body = f"Your parcel with tracking number {parcel['tracking_number']} has been received."
    send_email(subject, recipient, body)

def send_parcel_dispatched_email(parcel):
    subject = "Parcel Dispatched"
    recipient = parcel['sender_email']
    body = f"Your parcel with tracking number {parcel['tracking_number']} has been dispatched."
    send_email(subject, recipient, body)

def send_parcel_delivered_email(parcel):
    subject = "Parcel Delivered"
    recipient = parcel['sender_email']
    body = f"Your parcel with tracking number {parcel['tracking_number']} has been delivered."
    send_email(subject, recipient, body)

# Routes
@bp.route("/admin_dashboard")
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route("/dispatch_parcel/<tracking_number>", methods=['POST'])
@login_required
def dispatch_parcel(tracking_number):
    if request.method == "POST":
        parcel = mongo.db.parcels.find_one({'tracking_number': tracking_number})
        
        if not parcel:
            flash('Parcel not found!', 'danger')
            return redirect(url_for('main.dashboard'))

        # Update the parcel status to "Dispatched"
        mongo.db.parcels.update_one({'tracking_number': tracking_number}, {'$set': {'status': 'Dispatched'}})

        # Send the dispatched email
        send_parcel_dispatched_email(parcel)

        parcels = list(mongo.db.parcels.find({},{"_id":0, "tracking_number":1, "status":1}))
        flash('Parcel dispatched and email notification sent to sender.', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('dispatch_parcel.html', parcels=parcels, time=nigerian_time()) 

@bp.route("/deliver_parcel/<tracking_number>", methods=['POST'])
@login_required
def deliver_parcel(tracking_number):
    if request.method == "POST":

        parcel = mongo.db.parcels.find_one({'tracking_number': tracking_number})
        
        if not parcel:
            flash('Parcel not found!', 'danger')
            return redirect(url_for('main.dashboard'))

        # Update the parcel status to "Delivered"
        mongo.db.parcels.update_one({'tracking_number': tracking_number}, {'$set': {'status': 'Delivered'}})

        # Send the delivered email
        send_parcel_delivered_email(parcel)

        parcels = list(mongo.db.parcels.find({},{"_id":0, "tracking_number":1, "status":1}))
        flash('Parcel delivered and email notification sent to sender.', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('dispatch_parcel.html', time=nigerian_time())
