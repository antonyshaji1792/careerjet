from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, FileField, SelectMultipleField, widgets
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UserProfileForm(FlaskForm):
    skills = TextAreaField('Skills (comma-separated)', validators=[DataRequired()])
    experience = IntegerField('Years of Experience', validators=[DataRequired()])
    preferred_roles = TextAreaField('Preferred Roles (comma-separated)', validators=[DataRequired()])
    preferred_locations = TextAreaField('Preferred Locations (e.g. Remote, Hybrid, New York)', validators=[DataRequired()])
    submit = SubmitField('Update Profile')

class ScheduleForm(FlaskForm):
    daily_limit = IntegerField('Daily Application Limit', validators=[DataRequired()])
    daily_search_limit = IntegerField('Daily Search Limit (Jobs to scrape)', default=20, validators=[DataRequired()])
    is_autopilot_enabled = BooleanField('Enable AI Autopilot (Fully Automated)')
    preferred_days = SelectMultipleField('Preferred Days', 
                                       choices=[('Mon', 'Monday'), ('Tue', 'Tuesday'), ('Wed', 'Wednesday'), 
                                               ('Thu', 'Thursday'), ('Fri', 'Friday'), ('Sat', 'Saturday'), 
                                               ('Sun', 'Sunday')],
                                       option_widget=widgets.CheckboxInput(),
                                       widget=widgets.ListWidget(prefix_label=False),
                                       validators=[Optional()])
    start_time = StringField('Start Time', validators=[DataRequired()])
    end_time = StringField('End Time', validators=[DataRequired()])
    match_threshold = IntegerField('Minimum Match Score (%)', default=70, validators=[DataRequired()])
    submit = SubmitField('Save Schedule')
