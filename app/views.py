from app import create_app, mongo, mail
from flask import Blueprint, render_template, url_for, flash, redirect, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from flask_mail import Message
from flask_bcrypt import Bcrypt
from app.models import User
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
import stripe
import secrets
import os
import datetime
from bson.objectid import ObjectId
from functools import wraps

# Initialize the Blueprint
bp = Blueprint('main', __name__)

# Initialize extensions
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

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

def calculate_parcel_cost(weight, size):
    # pricing logic
    base_rate = 10.00
    weight_rate = 0.50
    size_rate = 0.25

    cost = base_rate + (float(weight) * weight_rate) + (float(size) * size_rate)
    return round(cost, 2)

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ParcelForm(FlaskForm):
    # Sender Information
    sender_name = StringField('Sender Name', validators=[DataRequired(), Length(min=2, max=50)])
    sender_phone = StringField('Sender Phone', validators=[DataRequired(), Length(min=10, max=15)])
    sender_address = TextAreaField('Sender Address', validators=[DataRequired(), Length(min=5, max=100)])

    # Recipient Information
    recipient_name = StringField('Recipient Name', validators=[DataRequired()])
    recipient_address = TextAreaField('Recipient Address', validators=[DataRequired()])
    recipient_phone = StringField('Recipient Phone', validators=[DataRequired(), Length(min=10, max=15)])

    # Parcel Information
    parcel_weight = FloatField('Parcel Weight (kg)', validators=[DataRequired()])
    parcel_size = StringField('Parcel Size (cm)', validators=[DataRequired(), Length(min=2, max=50)])
    delivery_instructions = TextAreaField('Delivery Instructions', validators=[Length(max=200)])

    submit = SubmitField('Book Parcel')

class PaymentForm(FlaskForm):
    amount = StringField('Amount', validators=[DataRequired()])
    submit = SubmitField('Pay Now')

# Routes
@bp.route("/")
def index():
    return render_template('index.html')

@bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = {
            'username': form.username.data,
            'email': form.email.data,
            'password': hashed_password,
            'role': 'user'
        }
        mongo.db.users.insert_one(user)
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard based on role if already authenticated
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # Fetch the user from the MongoDB database based on email
        user_dict = mongo.db.users.find_one({'email': form.email.data})
        
        # If user is found and the password is correct
        if user_dict and bcrypt.check_password_hash(user_dict['password'], form.password.data):
            # Create a User object from the user data dictionary
            user = User(user_dict)
            
            # Log in the user
            login_user(user)
            flash('Login successful. Welcome to your dashboard', 'success')

            # Check the user's role and redirect accordingly
            if user_dict.get('role') == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            else:
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        
        # If login fails
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    
    # Render the login page if the request is GET or if login fails
    return render_template('login.html', title='Login', form=form)

@bp.route("/logout")
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('main.index'))

@bp.route("/dashboard")
@login_required
def dashboard():
    parcels = list(mongo.db.parcels.find({'sender_id': str(current_user.get_id())}))
    return render_template('dashboard.html', parcels=parcels, time=nigerian_time())

@bp.route("/book_parcel", methods=['GET', 'POST'])
@login_required
def book_parcel():
    form = ParcelForm()

    if form.validate_on_submit():
        # Example calculation (replace with your actual calculation logic)
        weight = form.parcel_weight.data
        size = form.parcel_size.data
        cost = calculate_parcel_cost(weight, size)  # Define this function based on your pricing model

        # Store sender, recipient, and parcel details temporarily in the session
        session['parcel_info'] = {
            'recipient_name': form.recipient_name.data,
            'recipient_address': form.recipient_address.data,
            'recipient_phone': form.recipient_phone.data,
            'sender_name': form.sender_name.data,
            'sender_address': form.sender_address.data,
            'sender_phone': form.sender_phone.data,
            'parcel_weight': form.parcel_weight.data,
            'parcel_size': form.parcel_size.data,
            'delivery_instructions': form.delivery_instructions.data,
            'sender_id': str(current_user.get_id()),
            'sender_email': current_user.get_email(),
            'date_and_time': nigerian_time(),
            'cost': cost,
        }
        
        return redirect(url_for('main.payment'))

    return render_template('book_parcel.html', form=form)

@bp.route("/track_parcel", methods=['GET', 'POST'])
def track_parcel():
    tracking_number = request.args.get('tracking_number')
    parcel = mongo.db.parcels.find_one({'tracking_number': tracking_number})
    return render_template('track_parcel.html', parcel=parcel)

@bp.route("/payment", methods=['GET', 'POST'])
@login_required
def payment():
    form = PaymentForm()

    # Ensure that parcel details are stored before proceeding with payment
    if 'parcel_info' not in session:
        flash('Please enter parcel details before making a payment.', 'warning')
        return redirect(url_for('main.book_parcel'))

    if request.method == 'POST':
        amount = session['parcel_info']['cost']  # amount in session
        
        try:
            # Simulate payment processing logic (replace with Stripe payment logic)
            customer = stripe.Customer.create(
                email=current_user.get_email(),  # Current user's email
                source=request.form['stripeToken']  # Card token from Stripe form
            )
            charge = stripe.Charge.create(
                customer=customer.id,
                amount=int(float(amount) * 100),  # Amount in cents
                currency='usd',
                description='Courier Service Payment'
            )

            # Assuming payment is successful
            # session['payment_made'] = True  # Mark payment as made

            # Finalize the parcel Booking
            parcel_info = session.get('parcel_info')
            if parcel_info:
                tracking_number = secrets.token_hex(8)
                parcel = {
                    'tracking_number': tracking_number,
                    'sender_id': session['parcel_info']['sender_id'],
                    'sender_email': session['parcel_info']['sender_email'],
                    'sender_name': session['parcel_info']['sender_name'],
                    'sender_address': session['parcel_info']['sender_address'],
                    'sender_phone': session['parcel_info']['sender_phone'],
                    'recipient_name': session['parcel_info']['recipient_name'],
                    'recipient_address': session['parcel_info']['recipient_address'],
                    'recipient_phone': session['parcel_info']['recipient_phone'],
                    'parcel_weight': session['parcel_info']['parcel_weight'],
                    'parcel_size': session['parcel_info']['parcel_size'],
                    'delivery_instructions': session['parcel_info']['delivery_instructions'],
                    'date_and_time': session['parcel_info']['date_and_time'],
                    'cost': session['parcel_info']['cost'],
                    'status': 'Received'
                }
                mongo.db.parcels.insert_one(parcel)
                send_parcel_received_email(parcel)

                # Clear the session data
                session.pop('parcel_info', None)
                # session.pop('payment_made', None)  # Reset payment status after booking
                flash('Payment successful and parcel booked!', 'success')
                return redirect(url_for('main.confirm'))    # Redirect to confirmation page

        except stripe.error.StripeError as e:
            # Handle Stripe payment errors
            flash(f'Payment failed: {e.user_message}', 'danger')
            return redirect(url_for('main.payment'))
        except Exception as e:
            # Handle other possible errors
            flash(f'Error processing payment: {str(e)}', 'danger')
            return redirect(url_for('main.payment'))

    return render_template('payment.html', form=form, key=os.getenv('STRIPE_PUBLIC_KEY'))

@bp.route("/confirm")
def confirm():
    return render_template('confirm.html')
