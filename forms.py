from flask_wtf import FlaskForm
from wtforms import TextField, TextAreaField, SubmitField, validators, ValidationError
 
class ContactForm(FlaskForm):
  name = TextField("Nimi",  [validators.Required("Ole hyvä ja täytä nimesi")])
  email = TextField("Email",  [validators.Required("Ole hyvä ja täytä emailisi"), validators.Email("Email pitää olla muoto keke@mail.com")])
  subject = TextField("Aihe",  [validators.Required("Ole hyvä ja kirjoita aiheesi")])
  message = TextAreaField("Viesti",  [validators.Required("Ole hyvä ja kirjoita viesti")])
  submit = SubmitField("Lähetä")