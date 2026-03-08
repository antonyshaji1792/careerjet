from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField
from wtforms.validators import DataRequired

class ResumeGenerationForm(FlaskForm):
    target_role = StringField('Target Role', validators=[DataRequired()])
    tone = SelectField('Tone', choices=[('professional', 'Professional'), ('creative', 'Creative')], default='professional')
    job_description = TextAreaField('Job Description')
